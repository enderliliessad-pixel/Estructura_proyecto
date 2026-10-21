from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# creamos una clase que conecte con la base de datos
class Aprobacion(Base):
    # indicamos que la tabla es aprobaciones dentro del esquema vacaciones
    __tablename__ = "aprobaciones"
    __table_args__ = {"schema": "vacaciones"}
    # Las claves foráneas ya están definidas en PostgreSQL.
    id_aprobacion: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_solicitud: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    id_aprobador: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    fecha: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    observacion: Mapped[str | None] = mapped_column(Text, nullable=True)
# uso de mapped para definir el tipo de dato que va a tener
# mapped_column sirve para definir reglas de esa columna, como si es clave primaria o nulo, etc.