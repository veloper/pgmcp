from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .mixin import IsContentableMixin


class Sentence(IsContentableMixin, Base):
    # == Model Metadata =======================================================
    __tablename__   = "sentences"

    # == Columns ============================================================== 
    paragraph_id    : Mapped[int] = mapped_column(nullable=False)

    # == Relationships ========================================================

    # == Methods ==============================================================
