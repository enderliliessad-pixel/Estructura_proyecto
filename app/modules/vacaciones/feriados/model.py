from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# creamos una clase que conecte con la base de datos
class Feriado(Base):
    # indicamos que la tabla es feriados dentro del esquema vacaciones
    __tablename__ = "feriados"
    __table_args__ = {"schema": "vacaciones"}
    # Las claves foráneas ya están definidas en PostgreSQL.
    id_feriado: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    descripcion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tipo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estado: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
# uso de mapped para definir el tipo de dato que va a tener
# mapped_column sirve para definir reglas de esa columna, como si es clave primaria o nulo, etc.