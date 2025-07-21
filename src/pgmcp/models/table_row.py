from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.models.base import Base
from pgmcp.models.content import Content
from pgmcp.models.mixin import IsContentableMixin


if TYPE_CHECKING:
    from pgmcp.models.table import Table
    from pgmcp.models.table_row_cell import TableRowCell


class TableRow(IsContentableMixin, Base):
    # == Model Metadata =======================================================
    __tablename__ = "table_rows"

    # == Columns ============================================================== 
    table_id    : Mapped[int]         = mapped_column(ForeignKey("tables.id"), nullable=False)
    position    : Mapped[int]         = mapped_column(nullable=False, default=0)
    row_content : Mapped[str | None]  = mapped_column(nullable=True)

    # == Relationships ========================================================
    table           : Mapped[Table]                = relationship(
        "Table", back_populates="table_rows"
    )
    table_row_cells : Mapped[List[TableRowCell]]   = relationship(
        "TableRowCell",
        back_populates="table_row",
        cascade="all, delete-orphan",
        lazy="joined"
    )

    # == Methods ==============================================================
