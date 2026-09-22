import os
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import re
import csv
import unicodedata
import difflib
from tinytag import TinyTag
import yt_dlp

# --- LIBRERÍAS OPCIONALES PARA DOCX Y PDF ---
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import docx
except ImportError:
    docx = None

# --- EXPRESIONES REGULARES PRECOMPILADAS (OPTIMIZACIÓN) ---
REGEX_LIMPIEZA = re.compile(r'[-_.,()\[\]{}]+')
REGEX_ESPACIOS = re.compile(r'\s+')
REGEX_NUMEROS = re.compile(r'[\d\.]+')
REGEX_SOLO_DIGITOS = re.compile(r'\d+')
REGEX_PREFIJO_NUMERICO = re.compile(r'^\d+\s*[-_.]?\s*')

# --- VARIABLES GLOBALES ---
eleccion_usuario = None
evento_eleccion = threading.Event()

eleccion_yt = None
evento_yt = threading.Event()
ultimas_faltantes = []

persistencia_local_sort = {"col": None, "rev": False}

# --- CLASE ENTRY CON PLACEHOLDER ---
class PlaceholderEntry(tk.Entry):
    def __init__(self, master=None, placeholder="", color_ph="#888888", color_text="black", **kwargs):
        super().__init__(master, **kwargs)
        self.placeholder = placeholder
        self.color_ph = color_ph
        self.color_text = color_text
        self.bind("<FocusIn>", self._clear_ph)
        self.bind("<FocusOut>", self._set_ph)
        self._set_ph()
        
    def _set_ph(self, *args):
        if not self.get():
            self.insert(0, self.placeholder)
            self.config(fg=self.color_ph)
            
    def _clear_ph(self, *args):
        if self.get() == self.placeholder and self['fg'] == self.color_ph:
            self.delete(0, tk.END)
            self.config(fg=self.color_text)
            
    def set_text(self, text):
        self.delete(0, tk.END)
        self.config(fg=self.color_text)
        self.insert(0, text)
        
    def get_real_text(self):
        if self.get() == self.placeholder and self['fg'] == self.color_ph:
            return ""
        return self.get()

# --- FUNCIONES DE NORMALIZACIÓN ---
def normalizar_texto(texto):
    if not texto:
        return ""
    texto_norm = unicodedata.normalize('NFKD', str(texto))
    texto_sin_acentos = "".join([c for c in texto_norm if not unicodedata.combining(c)])
    texto_sub = texto_sin_acentos.replace('k', 'c').replace('K', 'C')
    limpio = REGEX_LIMPIEZA.sub(' ', texto_sub)
    limpio = REGEX_ESPACIOS.sub(' ', limpio).strip().lower()
    return limpio

# --- MOTOR DE LECTURA UNIVERSAL ---
def obtener_lista_canciones():
    input_texto = entrada_lista.get_real_text().strip()
    if not input_texto:
        return []
    
    if not os.path.exists(input_texto):
        return [c.strip() for c in input_texto.split(',') if c.strip()]
        
    ext = os.path.splitext(input_texto)[1].lower()
    canciones = []
    try:
        if ext == '.csv':
            with open(input_texto, 'r', encoding='utf-8-sig') as f: 
                lector = csv.reader(f, quotechar='"')
                encabezados = next(lector)
                try:
                    idx_track = encabezados.index('Track Name')
                    idx_artist = encabezados.index('Artist Name(s)')
                    for fila in lector:
                        if len(fila) > max(idx_track, idx_artist):
                            track = fila[idx_track].strip()
                            artist = fila[idx_artist].strip()
                            if track and artist:
                                canciones.append(f"{artist} - {track}")
                except ValueError:
                    for fila in lector:
                        if fila: canciones.append(fila[0].strip())
            log(f"★ ¡CSV procesado! {len(canciones)} canciones extraídas.", "exito")

        elif ext == '.pdf':
            if PyPDF2 is None:
                log("[X] Para leer PDFs necesitas instalar PyPDF2 (Abre la terminal y escribe: pip install PyPDF2)", "error")
            else:
                with open(input_texto, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            canciones.extend([linea.strip() for linea in text.split('\n') if linea.strip()])
                log(f"★ ¡PDF procesado! {len(canciones)} líneas extraídas.", "exito")

        elif ext == '.docx':
            if docx is None:
                log("[X] Para leer archivos Word necesitas python-docx (Abre la terminal y escribe: pip install python-docx)", "error")
            else:
                doc = docx.Document(input_texto)
                for para in doc.paragraphs:
                    if para.text.strip():
                        canciones.append(para.text.strip())
                log(f"★ ¡DOCX procesado! {len(canciones)} líneas extraídas.", "exito")

        else: 
            with open(input_texto, 'r', encoding='utf-8') as f:
                canciones = [linea.strip() for linea in f if linea.strip()]
            
    except Exception as e:
        log(f"[X] Error procesando archivo: {str(e)}", "error")
        
    return canciones

# --- FUNCIONES DE INTERFAZ BÁSICAS ---
def seleccionar_archivo():
    ruta = filedialog.askopenfilename(filetypes=[("Todos los archivos", "*.*"), ("Text files", "*.txt"), ("CSV", "*.csv")])
    if ruta:
        entrada_lista.set_text(ruta)

def seleccionar_origen():
    ruta = filedialog.askdirectory()
    if ruta:
        actual = entrada_origen.get_real_text()
        if actual:
            if ruta not in actual.split(";"):
                entrada_origen.set_text(actual + ";" + ruta)
        else:
            entrada_origen.set_text(ruta)

def seleccionar_destino():
    ruta = filedialog.askdirectory()
    if ruta:
        entrada_destino.set_text(ruta)

def limpiar_campos():
    entrada_lista.set_text("")
    entrada_origen.set_text("")
    entrada_destino.set_text("")
    
    entrada_lista._set_ph()
    entrada_origen._set_ph()
    entrada_destino._set_ph()
    
    caja_log.config(state=tk.NORMAL)
    caja_log.delete(1.0, tk.END)
    caja_log.config(state=tk.DISABLED)
    global ultimas_faltantes
    ultimas_faltantes = []
    log("🧹 Todos los campos y registros han sido limpiados.", "info")

def log(mensaje, tipo="normal"):
    if not ventana.winfo_exists(): return
    caja_log.config(state=tk.NORMAL)
    if tipo == "exito":
        caja_log.insert(tk.END, mensaje + "\n", "exito")
    elif tipo == "error":
        caja_log.insert(tk.END, mensaje + "\n", "error")
    elif tipo == "info":
        caja_log.insert(tk.END, mensaje + "\n", "info")
    elif tipo == "alerta":
        caja_log.insert(tk.END, mensaje + "\n", "alerta")
    else:
        caja_log.insert(tk.END, mensaje + "\n")
    caja_log.see(tk.END)
    caja_log.config(state=tk.DISABLED)

def obtener_nombre_unico(ruta_destino):
    if not os.path.exists(ruta_destino):
        return ruta_destino
    directorio, nombre_archivo = os.path.split(ruta_destino)
    nombre, ext = os.path.splitext(nombre_archivo)
    contador = 2
    while True:
        nuevo_nombre = f"{nombre}_{contador}{ext}"
        nueva_ruta = os.path.join(directorio, nuevo_nombre)
        if not os.path.exists(nueva_ruta):
            return nueva_ruta
        contador += 1

def ordenar_columna(tabla, col, reversa, ref_persistencia=None):
    l = [(tabla.set(k, col), k) for k in tabla.get_children('')]
    def clave_orden(elemento):
        texto = str(elemento[0])
        if col == "tamano":
            try: return float(REGEX_NUMEROS.findall(texto)[0])
            except: return 0.0
        elif col == "duracion":
            if ':' in texto:
                parts = texto.split(':')
                try: return int(parts[0])*60 + float(parts[1]) # Corrección aplicada
                except: return 0.0
            return 0.0
        elif col == "kbps" or col == "vistas":
            numeros = REGEX_SOLO_DIGITOS.findall(texto.replace('.', '').replace(',', ''))
            return float(numeros[0]) if numeros else -1
        return texto.lower()
    l.sort(key=clave_orden, reverse=reversa)
    for index, (_, k) in enumerate(l):
        tabla.move(k, '', index)
    if ref_persistencia is not None:
        ref_persistencia["col"] = col
        ref_persistencia["rev"] = reversa
    tabla.heading(col, command=lambda: ordenar_columna(tabla, col, not reversa, ref_persistencia))

# --- VENTANA LOCAL MULTIPLE ---
def preguntar_opcion(cancion, opciones):
    dialogo = tk.Toplevel(ventana)
    dialogo.title("Opciones Locales Múltiples")
    dialogo.geometry("920x350")
    dialogo.transient(ventana)
    dialogo.grab_set()

    tk.Label(dialogo, text="Hay varias opciones locales para:", font=("Segoe UI", 10)).pack(pady=(10, 0))
    tk.Label(dialogo, text=f"'{cancion}'", font=("Segoe UI", 13, "bold"), fg="#0078D7").pack(pady=2) 
    tk.Label(dialogo, text="Para descargar múltiples archivos, mantén presionada la tecla Ctrl o Shift al seleccionarlos.", font=("Segoe UI", 9, "italic"), fg="#444444").pack(pady=(0, 10))

    marco_tabla = tk.Frame(dialogo)
    marco_tabla.pack(fill="both", expand=True, padx=10, pady=5)
    
    columnas = ("nombre", "artista", "carpeta", "tamano", "duracion", "kbps")
    tabla = ttk.Treeview(marco_tabla, columns=columnas, show="headings", selectmode="extended")
    nombres_columnas = {
        "nombre": "Nombre", 
        "artista": "Artista / Grupo", 
        "carpeta": "Ubicación", 
        "tamano": "Tamaño", 
        "duracion": "Duración", 
        "kbps": "Calidad"
    }
    for col in columnas:
        tabla.heading(col, text=nombres_columnas[col], command=lambda c=col: ordenar_columna(tabla, c, False, persistencia_local_sort))
    
    tabla.column("nombre", width=240, anchor="w")
    tabla.column("artista", width=140, anchor="w")
    tabla.column("carpeta", width=130, anchor="w")
    tabla.column("tamano", width=80, anchor="center")
    tabla.column("duracion", width=70, anchor="center")
    tabla.column("kbps", width=70, anchor="center")
    tabla.pack(side="left", fill="both", expand=True)
    
    scrollbar = ttk.Scrollbar(marco_tabla, orient="vertical", command=tabla.yview)
    tabla.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    for op in opciones:
        carpeta_padre = os.path.basename(os.path.dirname(op))
        nombre_archivo = os.path.basename(op)
        tamano_mb = "N/A"
        duracion_str = "N/A"
        calidad = "N/A"
        artista_str = "Desconocido"
        try:
            tamano_mb = f"{os.path.getsize(op) / (1024 * 1024):.2f} MB"
        except: pass
        try:
            audio_info = TinyTag.get(op)
            if audio_info.artist:
                artista_str = audio_info.artist
            elif audio_info.albumartist:
                artista_str = audio_info.albumartist
            if audio_info.duration:
                m, s = divmod(int(audio_info.duration), 60)
                duracion_str = f"{m:02d}:{s:02d}"
            calidad = f"{int(audio_info.bitrate)} kbps" if audio_info.bitrate else "N/A"
        except: pass
        tabla.insert("", tk.END, values=(nombre_archivo, artista_str, carpeta_padre, tamano_mb, duracion_str, calidad))

    if persistencia_local_sort["col"] in columnas:
        ordenar_columna(tabla, persistencia_local_sort["col"], persistencia_local_sort["rev"], persistencia_local_sort)

    def confirmar(event=None):
        global eleccion_usuario
        selecciones = tabla.selection()
        if selecciones:
            eleccion_usuario = [opciones[tabla.index(s)] for s in selecciones]
        else:
            eleccion_usuario = None
        evento_eleccion.set()
        dialogo.destroy()

    def omitir(event=None):
        global eleccion_usuario
        eleccion_usuario = None
        evento_eleccion.set()
        dialogo.destroy()

    tabla.bind("<Double-1>", confirmar)
    frame_botones = tk.Frame(dialogo)
    frame_botones.pack(pady=10)
    tk.Button(frame_botones, text="Copiar Seleccionadas", command=confirmar, bg="green", fg="white").pack(side=tk.LEFT, padx=15)
    tk.Button(frame_botones, text="Ninguna (Buscar en YT)", command=omitir, bg="#333333", fg="white").pack(side=tk.RIGHT, padx=15)
    dialogo.protocol("WM_DELETE_WINDOW", omitir)

# --- VENTANA DE YOUTUBE MUSIC ---
def preguntar_opcion_yt(cancion, opciones_yt):
    dialogo = tk.Toplevel(ventana)
    dialogo.title("Búsqueda Oficial en YouTube Music")
    dialogo.geometry("900x350")
    dialogo.transient(ventana)
    dialogo.grab_set()

    tk.Label(dialogo, text="Audios Oficiales encontrados para:", font=("Segoe UI", 10)).pack(pady=(10, 0))
    tk.Label(dialogo, text=f"'{cancion}'", font=("Segoe UI", 13, "bold"), fg="#0078D7").pack(pady=2) 
    tk.Label(dialogo, text="Para descargar múltiples archivos, mantén presionada la tecla Ctrl o Shift al seleccionarlos.", font=("Segoe UI", 9, "italic"), fg="#444444").pack(pady=(0, 10))

    marco_tabla = tk.Frame(dialogo)
    marco_tabla.pack(fill="both", expand=True, padx=10, pady=5)
    
    columnas = ("titulo", "canal", "duracion", "tamano", "vistas")
    tabla = ttk.Treeview(marco_tabla, columns=columnas, show="headings", selectmode="extended")
    nombres_columnas = {"titulo": "Título de la Canción", "canal": "Canal / Artista", "duracion": "Duración", "tamano": "Tamaño Est.", "vistas": "Vistas"}
    
    for col in columnas:
        tabla.heading(col, text=nombres_columnas[col], command=lambda c=col: ordenar_columna(tabla, c, False))
        
    tabla.column("titulo", width=330, anchor="w")
    tabla.column("canal", width=140, anchor="w")
    tabla.column("duracion", width=70, anchor="center")
    tabla.column("tamano", width=80, anchor="center")
    tabla.column("vistas", width=90, anchor="center")
    tabla.pack(side="left", fill="both", expand=True)
    
    scrollbar = ttk.Scrollbar(marco_tabla, orient="vertical", command=tabla.yview)
    tabla.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    for op in opciones_yt:
        titulo = op.get('title', 'Desconocido')
        canal = op.get('uploader', 'Desconocido')
        dur = op.get('duration')
        
        if dur:
            m, s = divmod(int(dur), 60)
            dur_str = f"{m:02d}:{s:02d}"
            tamano_est = f"{(int(dur) * 128) / 8192:.2f} MB"
        else:
            dur_str = "N/A"
            tamano_est = "N/A"
            
        vistas = op.get('view_count')
        vistas_str = f"{vistas:,}".replace(',', '.') if vistas else "N/A"
        
        tabla.insert("", tk.END, values=(titulo, canal, dur_str, tamano_est, vistas_str))

    def confirmar(event=None):
        global eleccion_yt
        selecciones = tabla.selection()
        if selecciones:
            eleccion_yt = [opciones_yt[tabla.index(s)] for s in selecciones]
        else:
            eleccion_yt = None
        evento_yt.set()
        dialogo.destroy()

    def omitir(event=None):
        global eleccion_yt
        eleccion_yt = None
        evento_yt.set()
        dialogo.destroy()

    tabla.bind("<Double-1>", confirmar)
    frame_botones = tk.Frame(dialogo)
    frame_botones.pack(pady=10)
    tk.Button(frame_botones, text="Descargar Audio (.m4a)", command=confirmar, bg="#FF0000", fg="white", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=15)
    tk.Button(frame_botones, text="Omitir", command=omitir, bg="#333333", fg="white", font=("Segoe UI", 9, "bold")).pack(side=tk.RIGHT, padx=15)
    dialogo.protocol("WM_DELETE_WINDOW", omitir)

def descargar_video(url_bajar, titulo_bajar, ydl_opts_download):
    def tarea_hilo():
        log(f"Descargando - {titulo_bajar}", "info")
        try:
            with yt_dlp.YoutubeDL(ydl_opts_download) as ydl_down:
                ydl_down.download([url_bajar])
            log(f"{titulo_bajar} - Descargada", "exito")
        except Exception as e:
            error_msg = str(e)
            if "ffmpeg" in error_msg.lower() or "ffprobe" in error_msg.lower():
                log(f"[X] Falta 'ffmpeg.exe' en esta carpeta para poder convertir el audio de '{titulo_bajar}'.", "error")
            else:
                log(f"[X] Error descargando '{titulo_bajar}': {error_msg}", "error")
                
    hilo = threading.Thread(target=tarea_hilo, daemon=True)
    hilo.start()
    return hilo  

# --- MÓDULO YT-DLP ---
def descargar_faltantes_ytdlp(lista_faltantes=None):
    faltantes_a_bajar = lista_faltantes if lista_faltantes is not None else ultimas_faltantes
    if not faltantes_a_bajar:
        messagebox.showinfo("Sin faltantes", "No hay canciones pendientes para descargar.")
        return

    carpeta_destino = entrada_destino.get_real_text()
    if not carpeta_destino:
        messagebox.showwarning("Faltan datos", "Selecciona una carpeta destino primero.")
        return

    def tarea_ytdlp():
        global eleccion_yt
        log("\n==================================================", "info")
        log("🌐 Motor YouTube Music: Buscando audios oficiales...", "info")
        log("==================================================\n", "info")

        ydl_opts_search = {
            'extract_flat': True,
            'quiet': True
        }
        
        ydl_opts_download = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(carpeta_destino, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '192',
            }],
            'noplaylist': True,
            'quiet': True
        }

        if os.path.exists("cookies.txt"):
            ydl_opts_search['cookiefile'] = 'cookies.txt'
            ydl_opts_download['cookiefile'] = 'cookies.txt'

        hilos_descargas = []

        for cancion in faltantes_a_bajar:
            if not ventana.winfo_exists(): break
            log(f"🔍 Buscando - {cancion}...", "info")
            try:
                query_music = f"ytsearch5:{cancion} official audio"
                
                with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
                    info = ydl.extract_info(query_music, download=False)
                    
                    if 'entries' in info:
                        opciones = list(info['entries'])
                    else:
                        opciones = [info] if info else []
                
                if not opciones:
                    log(f"[X] No se encontraron resultados oficiales para '{cancion}'.", "error")
                    continue
                
                def es_oficial(op):
                    texto = str(op.get('title', '')).lower()
                    oficiales = ['official', 'oficial', 'music video', 'videoclip', 'audio']
                    return 1 if any(kw in texto for kw in oficiales) else 0

                opciones.sort(key=lambda x: (es_oficial(x), int(x.get('view_count') or 0)), reverse=True)

                evento_yt.clear()
                if ventana.winfo_exists():
                    ventana.after(0, preguntar_opcion_yt, cancion, opciones) 
                    evento_yt.wait()

                if eleccion_yt:
                    for video in eleccion_yt:
                        url_bajar = video.get('url')
                        titulo_bajar = video.get('title', 'Audio')
                        hilo_d = descargar_video(url_bajar, titulo_bajar, ydl_opts_download)
                        hilos_descargas.append(hilo_d)
                else:
                    log(f"[-] Omitida por el usuario: {cancion}", "alerta")

            except Exception as e:
                log(f"[X] Falló la búsqueda de '{cancion}': {str(e)}", "error")

        for h in hilos_descargas:
            if h.is_alive():
                h.join()

        if ventana.winfo_exists():
            log("\n==================================================", "info")
            log("★ ¡Descarga finalizada!", "exito")
            log("==================================================\n", "info")
            ventana.after(0, lambda: messagebox.showinfo("Terminado", "El proceso de descarga ha concluido."))
            
            boton_ejecutar.config(state=tk.NORMAL)
            btn_ytdlp.config(state=tk.NORMAL)
            btn_yt_directo.config(state=tk.NORMAL)

    if ventana.winfo_exists():
        boton_ejecutar.config(state=tk.DISABLED)
        btn_ytdlp.config(state=tk.DISABLED)
        btn_yt_directo.config(state=tk.DISABLED)
        hilo = threading.Thread(target=tarea_ytdlp, daemon=True)
        hilo.start()

# --- NUEVO: DESCARGA DIRECTA YT ---
def descargar_directo_youtube():
    carpeta_destino = entrada_destino.get_real_text()
    canciones = obtener_lista_canciones()

    if not canciones:
        messagebox.showwarning("Faltan datos", "Por favor ingresa canciones o selecciona un archivo válido.")
        return
        
    if not carpeta_destino:
        messagebox.showwarning("Faltan datos", "Por favor selecciona la carpeta destino.")
        return

    def tarea_directa():
        log("\n==================================================", "info")
        log("🚀 Iniciando descarga...", "info")
        log("==================================================\n", "info")

        ydl_opts_search = {
            'extract_flat': True, 
            'quiet': True
        }
        
        ydl_opts_download = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(carpeta_destino, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '192',
            }],
            'noplaylist': True,
            'quiet': True
        }

        if os.path.exists("cookies.txt"):
            ydl_opts_search['cookiefile'] = 'cookies.txt'
            ydl_opts_download['cookiefile'] = 'cookies.txt'

        hilos_descargas = []

        for cancion in canciones:
            if not ventana.winfo_exists(): break
            log(f"🔍 Buscando - {cancion}...", "info")
            try:
                query_music = f"ytsearch5:{cancion} official audio"
                
                with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
                    info = ydl.extract_info(query_music, download=False)
                    opciones = list(info['entries']) if 'entries' in info else ([info] if info else [])
                
                if not opciones:
                    log(f"[X] No se encontraron resultados oficiales para '{cancion}'.", "error")
                    continue
                
                def es_oficial(op):
                    texto = str(op.get('title', '')).lower()
                    oficiales = ['official', 'oficial', 'music video', 'videoclip', 'audio']
                    return 1 if any(kw in texto for kw in oficiales) else 0

                opciones.sort(key=lambda x: (es_oficial(x), int(x.get('view_count') or 0)), reverse=True)
                
                cancion_norm = normalizar_texto(cancion)
                mejor_opcion = opciones[0]
                
                for op in opciones:
                    titulo_op = normalizar_texto(op.get('title', ''))
                    similitud = difflib.SequenceMatcher(None, cancion_norm, titulo_op).ratio()
                    
                    if similitud > 0.45 or cancion_norm.split('-')[0].strip() in titulo_op:
                        mejor_opcion = op
                        break 
                
                url_bajar = mejor_opcion.get('url')
                titulo_bajar = mejor_opcion.get('title', 'Audio')
                
                hilo_d = descargar_video(url_bajar, titulo_bajar, ydl_opts_download)
                hilos_descargas.append(hilo_d)

            except Exception as e:
                log(f"[X] Falló la búsqueda de '{cancion}': {str(e)}", "error")

        for h in hilos_descargas:
            if h.is_alive():
                h.join()

        if ventana.winfo_exists():
            log("\n==================================================", "info")
            log("★ ¡Descarga finalizada!", "exito")
            log("==================================================\n", "info")
            ventana.after(0, lambda: messagebox.showinfo("Terminado", "El proceso de descarga ha concluido."))
            
            boton_ejecutar.config(state=tk.NORMAL)
            btn_ytdlp.config(state=tk.NORMAL)
            btn_yt_directo.config(state=tk.NORMAL)

    if ventana.winfo_exists():
        boton_ejecutar.config(state=tk.DISABLED)
        btn_ytdlp.config(state=tk.DISABLED)
        btn_yt_directo.config(state=tk.DISABLED)
        hilo = threading.Thread(target=tarea_directa, daemon=True)
        hilo.start()

def prompt_descargar_faltantes(faltantes):
    if not faltantes: return
    if not ventana.winfo_exists(): return
    resp = messagebox.askyesno(
        "Cacería en YouTube Music",
        f"Faltan {len(faltantes)} canciones.\n¿Quieres buscar las versiones oficiales en YouTube Music para descargarlas en .m4a?"
    )
    if resp:
        descargar_faltantes_ytdlp(faltantes)

# --- PROCESO PRINCIPAL DE COPIADO LOCAL ---
def procesar_canciones():
    global ultimas_faltantes
    canciones = obtener_lista_canciones()
    rutas_origen_cruda = entrada_origen.get_real_text()
    carpeta_destino = entrada_destino.get_real_text()

    if not canciones or not rutas_origen_cruda or not carpeta_destino:
        messagebox.showwarning("Faltan datos", "Parcero, por favor revisa que las rutas y/o textos estén completos.")
        return

    boton_ejecutar.config(state=tk.DISABLED)
    btn_ytdlp.config(state=tk.DISABLED)
    btn_yt_directo.config(state=tk.DISABLED)
    
    caja_log.config(state=tk.NORMAL)
    caja_log.delete(1.0, tk.END)
    caja_log.config(state=tk.DISABLED)
    
    log("==================================================", "info")
    log("▶ Arrancando el motor de búsqueda local...", "info")
    log("==================================================\n", "info")

    def tarea():
        global eleccion_usuario, ultimas_faltantes
        total_encontradas = 0
        total_no_encontradas = 0
        lista_faltantes_actual = []

        try:
            carpetas = [c.strip() for c in rutas_origen_cruda.split(";") if c.strip()]
            archivos_locales = []
            
            for carpeta in carpetas:
                if os.path.exists(carpeta):
                    for raiz, dirs, archivos in os.walk(carpeta):
                        for archivo in archivos:
                            if archivo.lower().endswith(('.mp3', '.m4a', '.flac', '.wav', '.ogg')):
                                archivos_locales.append(os.path.join(raiz, archivo))

            for cancion in canciones:
                if not ventana.winfo_exists(): break
                if " - " in cancion:
                    artista, titulo = cancion.split(" - ", 1)
                else:
                    artista, titulo = "", cancion

                titulo_norm = normalizar_texto(titulo)
                palabras_titulo = set(p for p in titulo_norm.split(' ') if len(p) > 2)

                coincidencias = []
                for ruta_completa in archivos_locales:
                    nombre_archivo = os.path.basename(ruta_completa)
                    nombre_base = os.path.splitext(nombre_archivo)[0]
                    nombre_sin_num = REGEX_PREFIJO_NUMERICO.sub('', nombre_base)
                    nombre_norm = normalizar_texto(nombre_sin_num)

                    match_cond = False
                    if titulo_norm and nombre_norm and (titulo_norm in nombre_norm or nombre_norm in titulo_norm):
                        match_cond = True
                    elif palabras_titulo:
                        palabras_nombre = set(p for p in nombre_norm.split(' ') if len(p) > 2)
                        overlap = len(palabras_titulo.intersection(palabras_nombre))
                        if overlap >= max(1, len(palabras_titulo) * 0.6):
                            match_cond = True
                    
                    if not match_cond and titulo_norm and nombre_norm:
                        ratio = difflib.SequenceMatcher(None, titulo_norm, nombre_norm).ratio()
                        if ratio > 0.68:
                            match_cond = True

                    if match_cond:
                        coincidencias.append(ruta_completa)

                if len(coincidencias) == 0:
                    log(f"[X] No encontrada local: {cancion}", "error")
                    total_no_encontradas += 1
                    lista_faltantes_actual.append(cancion)
                
                elif len(coincidencias) == 1:
                    archivo_a_copiar = coincidencias[0]
                    destino = os.path.join(carpeta_destino, os.path.basename(archivo_a_copiar))
                    destino = obtener_nombre_unico(destino)
                    shutil.copy2(archivo_a_copiar, destino)
                    log(f"[✓] Copiada: {os.path.basename(destino)}", "exito")
                    total_encontradas += 1
                
                else:
                    evento_eleccion.clear()
                    if ventana.winfo_exists():
                        ventana.after(0, preguntar_opcion, cancion, coincidencias) 
                        evento_eleccion.wait() 

                    if eleccion_usuario and isinstance(eleccion_usuario, list):
                        for ruta_elegida in eleccion_usuario:
                            destino = os.path.join(carpeta_destino, os.path.basename(ruta_elegida))
                            destino = obtener_nombre_unico(destino)
                            shutil.copy2(ruta_elegida, destino)
                            log(f"[✓] Copiada (Manual): {os.path.basename(destino)}", "exito")
                        total_encontradas += 1
                    else:
                        log(f"[X] Ninguna local. Fila de YouTube: {cancion}", "alerta")
                        total_no_encontradas += 1
                        lista_faltantes_actual.append(cancion)

            ultimas_faltantes = lista_faltantes_actual

            if ventana.winfo_exists():
                log("\n==================================================", "info")
                log(f"★ Locales finalizadas | Encontradas: {total_encontradas} | Faltantes: {total_no_encontradas}", "exito")
                
                if ultimas_faltantes:
                    ventana.after(0, lambda: prompt_descargar_faltantes(ultimas_faltantes))

        except Exception as e:
            if ventana.winfo_exists(): log(f"\n[Error]: {str(e)}", "error")
        finally:
            if ventana.winfo_exists():
                boton_ejecutar.config(state=tk.NORMAL)
                btn_ytdlp.config(state=tk.NORMAL)
                btn_yt_directo.config(state=tk.NORMAL)

    if ventana.winfo_exists():
        hilo = threading.Thread(target=tarea, daemon=True)
        hilo.start()

# --- INTERFAZ ---
ventana = tk.Tk()
ventana.title("Spotify Local Matcher Pro + YouTube Music")
ventana.geometry("880x530")  
ventana.config(padx=15, pady=15)
ventana.columnconfigure(1, weight=1) 

fuente_etiquetas = ("Segoe UI", 9)

tk.Label(ventana, text="1. Canciones/Archivo:", font=fuente_etiquetas).grid(row=0, column=0, sticky="w", pady=5)
entrada_lista = PlaceholderEntry(ventana, placeholder="1- Selecciona el archivo que contiene el nombre de las canciones ó escribe el nombre para descargarla", width=65, font=fuente_etiquetas)
entrada_lista.grid(row=0, column=1, padx=5, sticky="ew") 
tk.Button(ventana, text="Buscar Archivo", command=seleccionar_archivo, font=fuente_etiquetas).grid(row=0, column=2, columnspan=2, sticky="ew", padx=2)

tk.Label(ventana, text="2. Origen Local:", font=fuente_etiquetas).grid(row=1, column=0, sticky="w", pady=5)
entrada_origen = PlaceholderEntry(ventana, placeholder="2- Selecciona la carpeta donde tienes tus canciones (Deja en blanco si quieres descargarlas)", width=65, font=fuente_etiquetas)
entrada_origen.grid(row=1, column=1, padx=5, sticky="ew")
tk.Button(ventana, text="Añadir Carpeta", command=seleccionar_origen, font=fuente_etiquetas).grid(row=1, column=2, columnspan=2, sticky="ew", padx=2)

tk.Label(ventana, text="3. Carpeta Destino:", font=fuente_etiquetas).grid(row=2, column=0, sticky="w", pady=5)
entrada_destino = PlaceholderEntry(ventana, placeholder="3- Selecciona la carpeta donde se guardaran tus canciones", width=65, font=fuente_etiquetas)
entrada_destino.grid(row=2, column=1, padx=5, sticky="ew")
tk.Button(ventana, text="Buscar", command=seleccionar_destino, font=fuente_etiquetas).grid(row=2, column=2, columnspan=2, sticky="ew", padx=2)

frame_acciones = tk.Frame(ventana)
frame_acciones.grid(row=3, column=0, columnspan=4, pady=15, sticky="ew")

boton_ejecutar = tk.Button(frame_acciones, text="¡Empezar a Copiar Locales!", bg="#2E8B57", fg="white", font=("Segoe UI", 10, "bold"), command=procesar_canciones, relief=tk.FLAT)
boton_ejecutar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5), ipady=5)

btn_limpiar = tk.Button(frame_acciones, text="🧹 Limpiar Todo", bg="#FF9800", fg="white", font=("Segoe UI", 10, "bold"), command=limpiar_campos, relief=tk.FLAT)
btn_limpiar.pack(side=tk.LEFT, fill=tk.X, expand=False, padx=(5, 5), ipady=5)

btn_ytdlp = tk.Button(frame_acciones, text="🌐 Descargar Faltantes", bg="#FF0000", fg="white", font=("Segoe UI", 10, "bold"), command=lambda: descargar_faltantes_ytdlp(ultimas_faltantes), relief=tk.FLAT)
btn_ytdlp.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5), ipady=5)

btn_yt_directo = tk.Button(frame_acciones, text="🚀 Descargar Directo", bg="#D32F2F", fg="white", font=("Segoe UI", 10, "bold"), command=descargar_directo_youtube, relief=tk.FLAT)
btn_yt_directo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0), ipady=5)

marco_log = tk.Frame(ventana, bg="#1E1E1E", bd=2, relief=tk.SUNKEN)
marco_log.grid(row=4, column=0, columnspan=4, sticky="nsew")
ventana.rowconfigure(4, weight=1)

caja_log = tk.Text(marco_log, width=70, height=12, font=("Consolas", 10), bg="#1E1E1E", fg="#D4D4D4", borderwidth=0, padx=10, pady=10)
caja_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scroll_log = tk.Scrollbar(marco_log, command=caja_log.yview, bg="#333333")
caja_log.configure(yscrollcommand=scroll_log.set)
scroll_log.pack(side=tk.RIGHT, fill=tk.Y)

caja_log.tag_config("exito", foreground="#4CAF50", font=("Consolas", 10, "bold"))
caja_log.tag_config("error", foreground="#F44336")
caja_log.tag_config("info", foreground="#569CD6")
caja_log.tag_config("alerta", foreground="#FFEB3B")
caja_log.config(state=tk.DISABLED)

ventana.mainloop()