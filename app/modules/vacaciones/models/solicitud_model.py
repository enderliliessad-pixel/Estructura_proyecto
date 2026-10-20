from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# creamos una clase que conecte con la base de datos
class Solicitud(Base):
    # indicamos que la tabla es saldos dentro del esquema vacaciones
    __tablename__ = "solicitudes"
    __table_args__ = {"schema": "vacaciones"}
    # las relaciones con core empleado estan en la base de datos
    id_solicitud: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_empleado: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tipo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fecha_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    dias_solicitados: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    horas_solicitadas: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fecha_solicitud: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
# uso de mapped para definir el tipo de dato que va a tener
# mapped_column sirve para definir reglas de esa columna, como si es clave primaria o nulo, etc.