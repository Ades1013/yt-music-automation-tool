# 🎵 Spotify Local Matcher & YT Music Downloader

Una aplicación de escritorio desarrollada en **Python** orientada a la automatización de bibliotecas musicales. Su objetivo principal es optimizar tu colección local cruzando datos de Spotify y automatizando descargas desde YouTube Music sin bloquear la experiencia de usuario.

## 🚀 Requisitos para el Usuario Final (.exe)

Para que el archivo ejecutable (`app_musica.exe`) funcione al 100% y no sufra bloqueos por parte de YouTube, **debes colocar los siguientes archivos en la misma carpeta donde ejecutes el programa**:

1. **`ffmpeg.exe` (Obligatorio):** Requerido por el motor de descargas para procesar, corregir y convertir los audios a formatos reproducibles (`.m4a`/`.mp3`). Si falta, algunas canciones descargadas no se podrán reproducir.
2. **`cookies.txt` (Altamente Recomendado):** Evita que YouTube tome la aplicación como un bot (errores `403 Forbidden`) y permite descargar canciones con restricción de edad. 
   * *¿Cómo obtenerlo?* Instala una extensión en tu navegador (como *Get cookies.txt LOCALLY*), entra a YouTube Music, exporta tus cookies como `cookies.txt` y colócalo al lado del programa.

*La estructura de tu carpeta debe lucir así:*
```text
📂 Mi Carpeta de Música
 ├── 📄 app_musica.exe
 ├── 📄 ffmpeg.exe
 └── 📄 cookies.txt
```

## 🚀 Características principales

* **Procesamiento de Datos:** Importa archivos CSV exportados desde Spotify y los normaliza automáticamente.
* **Algoritmo de Coincidencia (Matching):** Compara los metadatos y el nombre de los archivos en tus directorios locales para encontrar similitudes, utilizando algoritmos de coincidencia de secuencias (`difflib`) y expresiones regulares (`regex`).
* **Automatización Web:** Se integra de forma nativa con `yt-dlp` para ejecutar búsquedas automáticas en YouTube Music, descargando los audios faltantes en formato **AAC/M4A nativo** para evitar dependencias externas lentas.
* **Multithreading:** La interfaz gráfica opera de forma fluida y sin congelamientos gracias a la implementación de hilos en segundo plano para procesar descargas concurrentes.

## 🛠️ Tecnologías utilizadas

* **Lenguaje:** Python 3
* **Interfaz Gráfica:** Tkinter
* **Core de Descargas:** yt-dlp (Soporte de cookies integrado)
* **Conversión de Audio:** FFmpeg

## 📦 Requisitos previos de Desarrollo

Si eres programador y quieres ejecutar o modificar el código fuente (`app_musica.py`):

1. Asegúrate de tener instalado **Python 3** en tu sistema.
2. Clona este repositorio:
   ```bash
   git clone https://github.com
   ```
3. Instala las dependencias requeridas desde la raíz del proyecto:
   ```bash
   pip install -r requisitos.txt
   ```
4. Ejecuta el entorno gráfico:
   ```bash
   python app_musica.py
   ```

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.

