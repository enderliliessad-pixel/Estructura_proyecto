# API de Vacaciones — ITQ Conecta

Backend de consultas desarrollado con FastAPI, SQLAlchemy y PostgreSQL.


## 1. Requisitos

- Python con soporte para las versiones que contiene el archivo `requirements.txt`.
- PostgreSQL instalado y en ejecución, con la extensión `uuid-ossp` activada.
- DBeaver o la herraminta de uso para consultas sql
- Un usuario de PostgreSQL con permisos para crear la base, esquemas, tablas y extensión.

Abre la terminal en la carpeta `Vacaciones`, donde están este README y `requirements.txt`.

## 2. Entorno virtual e instalación

En Windows, desde PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Si prefieres trabajar sin activar el entorno aunque pueden existir problemas con otras apps

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

En Linux o macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 3. Configuración de la conexión

Si todavía no tienes un `.env`, copia el ejemplo. No sobrescribas tu configuración existente.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux o macOS:

```bash
cp .env.example .env
```

Edita el `.env` de la raíz con los datos de tu servidor:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gestion_vacaciones_itq
DB_USER=postgres
DB_PASSWORD=CAMBIA_POR_TU_CONTRASENA_LOCAL
```

## 4. Creacion de la base de datos
Se va a crar una base de datos siguiento la infraestructura propuesta por el itq, existe un ejemplo especifico para vacaciones en sql
Se tiene que incrementar una tabla para poder realizar la division de los dias antiguos y los nuevos, se encuentra el sql en la carpeta con el mismo nombre y se llama periodos y descuentos


## 5. Iniciar el servidor 

Con el entorno activado y el `.env` configurado:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Documentación de la API: <http://127.0.0.1:8000/docs>.





Las rutas del módulo usan el prefijo `/api/v1/vacaciones`.
En una base recién creada, las consultas de listas devolverán listas vacías hasta registrar datos en la base de datos
