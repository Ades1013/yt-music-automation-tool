Spotify Local Matcher & YT Music Downloader.

Aplicación de escritorio desarrollada en Python orientada a la automatización de bibliotecas musicales.

Características Principales

Procesamiento de Datos: Importa archivos CSV exportados desde Spotify y los normaliza.

Algoritmo de Coincidencia (Matching): Compara los metadatos y el nombre de los archivos en directorios locales para encontrar similitudes, utilizando algoritmos de coincidencia de secuencias (difflib) y expresiones regulares.

Automatización Web: Se integra con yt-dlp para ejecutar búsquedas automáticas en YouTube Music, descargar los audios faltantes en formato AAC/M4A nativo y evitar dependencias externas lentas.

Multithreading: La interfaz gráfica (Tkinter) opera de forma fluida y sin bloqueos gracias a la implementación de hilos en segundo plano para las descargas concurrentes.

Tecnologías utilizadas
Python 3, Tkinter, yt-dlp, Multithreading, Regex.
