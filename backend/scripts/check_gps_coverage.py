#!/usr/bin/env python3
"""Quick check of GPS data coverage in assets."""
import sys
from pathlib import Path

# Add parent directory (backend root) to path
backend_root = Path(__file__).parents[1]
sys.path.insert(0, str(backend_root))

from app.db.session import SessionLocal
from app.models.asset import Asset

db = SessionLocal()
try:
    total = db.query(Asset).count()
    with_gps = db.query(Asset).filter(
        Asset.gps_latitude.isnot(None),
        Asset.gps_longitude.isnot(None)
    ).count()
    print(f'Total assets: {total}')
    print(f'Assets with GPS: {with_gps}')
    if total > 0:
        print(f'Coverage: {100*with_gps/total:.1f}%')
finally:
    db.close()
