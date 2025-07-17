from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.models.base import Base
from pgmcp.models.mixin import IsContentableMixin


if TYPE_CHECKING:
    from pgmcp.models.table_row import TableRow


class TableRowCell(IsContentableMixin, Base):
    # == Model Metadata =======================================================
    __tablename__ = "table_row_cells"

    # == Columns ============================================================== 
    table_row_id  : Mapped[int]         = mapped_column(nullable=False)
    position      : Mapped[int]         = mapped_column(nullable=False, default=0)
    cell_content  : Mapped[str | None]  = mapped_column(nullable=True)

    # == Relationships ========================================================
    table_row     : Mapped["TableRow"]  = relationship("TableRow", back_populates="table_row_cells")

    # == Methods ==============================================================
