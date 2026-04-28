from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.provenance import Provenance
from sqlalchemy import inspect

db = SessionLocal()

sha256 = '1c8ead716ba5b2750c9890f6e941c1de8b31da4599b050e35d3befb3d8873cc0'
asset = db.query(Asset).filter(Asset.sha256 == sha256).first()

if asset:
    print('=== Asset Record Details ===\n')
    mapper = inspect(asset.__class__)
    for column in mapper.columns:
        value = getattr(asset, column.name)
        print(f'{column.name}: {value}')
    
    # Check for storage validation records
    print('\n=== Related Records ===')
    provs = db.query(Provenance).filter(Provenance.asset_sha256 == sha256).all()
    print(f'Provenance count: {len(provs)}')
    for p in provs:
        print(f'  Source: {p.source_path}')

db.close()
