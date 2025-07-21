from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.models.base import Base
from pgmcp.models.content import Content
from pgmcp.models.mixin import IsContentableMixin, IsListableMixin, IsSectionableMixin


if TYPE_CHECKING:
    from pgmcp.models.table_row import TableRow

class Table(IsContentableMixin, IsSectionableMixin, IsListableMixin, Base):
    # == Model Metadata =======================================================
    __tablename__      = "tables"

    # == Columns ============================================================== 
    position           : Mapped[int] = mapped_column(nullable=False, default=0)

    # == Relationships ========================================================
    table_rows         : Mapped[list["TableRow"]] = relationship(
        "TableRow",
        back_populates="table",
        cascade="all, delete-orphan",
        lazy="joined"
    )

    # == Methods ==============================================================
