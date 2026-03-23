from __future__ import annotations

from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine

DB_PATH = Path(__file__).resolve().parent / "data" / "ikv_portal.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


def init_db() -> None:
    """Create tables.

    In deze versie is een database-reset de standaard aanpak bij grote schema
    uitbreidingen (zoals ViiZ-achtige velden). Daardoor vermijden we fragiele
    'best-effort' ALTER TABLE migraties.
    """
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)
