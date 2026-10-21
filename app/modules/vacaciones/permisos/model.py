from datetime import date, time
from decimal import Decimal

from sqlalchemy import BigInteger, Date, Numeric, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# creamos una clase que conecte con la base de datos
class Permiso(Base):
    # indicamos que la tabla es permisos dentro del esquema vacaciones
    __tablename__ = "permisos"
    __table_args__ = {"schema": "vacaciones"}

    id_permiso: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # La clave foránea hacia core.empleados ya existe en PostgreSQL.
    id_empleado: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    hora_inicio: Mapped[time | None] = mapped_column(Time, nullable=True)
    hora_fin: Mapped[time | None] = mapped_column(Time, nullable=True)
    total_horas: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str | None] = mapped_column(String(50), nullable=True)
# uso de mapped para definir el tipo de dato que va a tener
# mapped_column sirve para definir reglas de esa columna, como si es clave primaria o nulo, etc.