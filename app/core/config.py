from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL
from functools import lru_cache

# este archivo tiene la finalidad de cargar el .env y preparamos la direccion a la que nos conectaremos a la base
# usamos el resolve para indicar que es una ruta absoluta y los 2 parents para ir mas arriba donde esta el .env
ruta_env = Path(__file__).resolve().parent.parent / ".env"


class Configuracion(BaseSettings):
    #indicamos de donde se cargara el archivo
    model_config = SettingsConfigDict(
        env_file=ruta_env / ".env",
        #indicamos el formato de lectura
        env_file_encoding="utf-8",
        # extra ignore para que pydantic ignore cualquier dato extra de mi .env
        extra="ignore",
        # por si ocurre un error de sintaxis al colocar nombres, contraseñas etc, no apareceran
        hide_input_in_errors=True,
    )

    # nombre de mi base indicando que tiene que estar llena
    db_host: str = Field(min_length=1)
    # puerto por defecto de postgres y ge y le para indicar que el rango valido
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = Field(min_length=1)
    # nombre del usuario de la base de datos
    db_user: str = Field(min_length=1)
    # contraseña de la base y uso de secretStr para que la contraseña no aparesca,(no es un cifrado)
    db_password: SecretStr
    # funcion para conectar la base de datos.

    def url_base_datos(self):

        # url.create es una fomra segura de crear una conexion, u create para poder leer cualquier tipo de caracter especial
        url_conexion = URL.create(
            "postgresql+asyncpg",
            username=self.db_user,
            # el get_secret_value trae la contraseña solo para construir la conexion con la base y nada mas
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

        # devolvemos la conexion construida
        return url_conexion


# Creamos el objeto que carga y valida los datos de configuración una sola vez
@lru_cache()
def obtener_configuracion():
    return Configuracion()