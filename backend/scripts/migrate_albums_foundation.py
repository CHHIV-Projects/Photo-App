"""One-time schema sync script for Milestone 11.10 album foundation."""

from __future__ import annotations

from app.db.session import SessionLocal
from app.services.albums.album_schema import ensure_album_schema


def main() -> None:
    db_session = SessionLocal()
    try:
        summary = ensure_album_schema(db_session)
    finally:
        db_session.close()

    print("Album schema sync complete")
    print(f"  created_tables={summary.created_tables}")
    print(f"  created_indexes={summary.created_indexes}")


if __name__ == "__main__":
    main()
