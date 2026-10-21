from decimal import Decimal

from sqlalchemy import BigInteger, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# creamos una clase que conecte con la base de datos
class Saldo(Base):
    # indicamos que la tabla es saldos dentro del esquema vacaciones
    __tablename__ = "saldos"
    __table_args__ = {"schema": "vacaciones"}
    # las relaciones con core empleado estan en la base de datos
    id_saldo: Mapped[int] = mapped_column(BigInteger, primary_key=True)    
    id_empleado: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    periodo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    dias_asignados: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    dias_utilizados: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    dias_disponibles: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
# uso de mapped para definir el tipo de dato que va a tener
# mapped_column sirve para definir reglas de esa columna, como si es clave primaria o nulo, etc.