from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.provenance import Provenance

db = SessionLocal()

print('=== Searching for (3).jpg in database ===\n')

assets = db.query(Asset).all()
print(f'Total assets in DB: {len(assets)}')

provs = db.query(Provenance).filter(Provenance.source_path.like('%(3).jpg%')).all()
print(f'Provenances with exact "(3).jpg" in source_path: {len(provs)}\n')

if not provs:
    # Also try checking Asset records directly for vault files
    import os
    vault_path = 'C:\\Users\\chhen\\My Drive\\AI Photo Organizer\\Photo Organizer_v1\\storage\\vault'
    print(f'Checking vault directory for related files...')
    
    # Search for assets that might render (3).jpg
    for root, dirs, files in os.walk(vault_path):
        for file in files:
            if '3' in file and file.endswith('.jpg'):
                full_path = os.path.join(root, file)
                asset = db.query(Asset).filter(Asset.vault_path == full_path).first()
                if asset:
                    provs_for_asset = db.query(Provenance).filter(Provenance.asset_sha256 == asset.sha256).all()
                    print(f'\n  Found asset: {asset.sha256}')
                    print(f'  Vault path: {asset.vault_path}')
                    print(f'  Provenance count: {len(provs_for_asset)}')
                    if provs_for_asset:
                        for p in provs_for_asset[:2]:
                            print(f'    Source: {p.source_path}')
else:
    print('Matching records:')
    for p in provs[:10]:
        print(f'  SHA256: {p.asset_sha256}')
        print(f'  Source path: {p.source_path}')
        print(f'  Source relative path: {p.source_relative_path}')
        asset = db.query(Asset).filter(Asset.sha256 == p.asset_sha256).first()
        print(f'  Asset exists: {asset is not None}')
        if asset:
            print(f'  Asset vault_path: {asset.vault_path}')
        print()

db.close()
