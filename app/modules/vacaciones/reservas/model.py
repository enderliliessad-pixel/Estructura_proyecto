from datetime import datetime
from decimal import Decimal
from sqlalchemy import BigInteger, Boolean, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

# clase para guardar de que periodo se apartaron los dias de una solicitud
class Reserva(Base):
    __tablename__ = "reservas_por_periodo"
    __table_args__ = {"schema": "vacaciones"}
    id_reserva: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_empleado: Mapped[int] = mapped_column(BigInteger)
    id_solicitud: Mapped[int] = mapped_column(BigInteger)
    id_saldo: Mapped[int] = mapped_column(BigInteger)
    dias_reservados: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    es_anticipo: Mapped[bool] = mapped_column(Boolean)
    estado: Mapped[str] = mapped_column(String(20))
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fecha_cierre: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

# clase para registrar el descuento definitivo sin perder el periodo de origen
class Descuento(Base):
    __tablename__ = "descuentos_por_periodo"
    __table_args__ = {"schema": "vacaciones"}
    id_descuento: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_empleado: Mapped[int] = mapped_column(BigInteger)
    id_solicitud: Mapped[int] = mapped_column(BigInteger)
    id_saldo: Mapped[int] = mapped_column(BigInteger)
    dias_descontados: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    es_anticipo: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True))
