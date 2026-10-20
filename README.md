# Guia para ejecutar el proyecto
1. Clona el repositorio
2. Crea un entorno virtual para que las librerias no creen conflico con otros programas
"(python -m venv .venv)"
3. Activa el etorno virtual
".\.venv\Scripts\Activate.ps1"
4. El entorno estara instalado porque se observara un .venv en la terminal de color verde
5. Instala las dependencias encontradas en el .txt de este proyecto
Creas un archivo .env donde estaran los datos de conexion con la base
Estos son los datos de la base que se deben llenar
DB_HOST=nombre
DB_PORT=numero de puerto
DB_NAME=nombre de la base
DB_USER=nombre usuario
DB_PASSWORD=contraseña
6. una vez terminado vas a iniciar el servidor
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
7. Una vez el servicor este iniciado ingresa al siguiente link
http://127.0.0.1:8000/docs


Y listo. 