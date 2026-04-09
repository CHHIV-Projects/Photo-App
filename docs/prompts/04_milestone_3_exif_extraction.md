Build the next milestone: EXIF extraction and persistence.

Goal:

Extract objective EXIF metadata from stored assets and save it into PostgreSQL.

Scope:

\- work only with assets already stored in the database

\- read each asset's vault_path

\- extract objective EXIF metadata from the file

\- write extracted metadata back to the database

\- keep this milestone focused and minimal

Important constraints:

\- do not build scan-era estimation yet

\- do not build AI classification yet

\- do not build OCR yet

\- do not build landmark recognition yet

\- do not build user-facing API endpoints yet

\- do not overengineer

\- keep code modular, readable, and beginner-friendly

Recommended tool:

\- use ExifTool via Python

\- prefer a simple wrapper approach

\- handle missing EXIF gracefully

Required behavior:

1\. Add nullable EXIF-related fields to the Asset model for:

\- exif_datetime_original

\- exif_create_date

\- gps_latitude

\- gps_longitude

\- camera_make

\- camera_model

\- lens_model

2\. Create a metadata extraction service that:

\- accepts one asset or a list of assets

\- reads metadata from the asset's vault_path

\- returns structured extraction results

\- handles files with missing EXIF without failing the whole run

\- handles extraction errors gracefully

3\. Create a persistence/update service that:

\- updates existing Asset rows with extracted EXIF values

\- does not create new assets

\- tracks:

\- updated assets

\- skipped assets

\- failed assets with reasons

4\. Create a test runner script that:

\- loads assets from the database

\- extracts EXIF for them

\- updates the database

\- prints a summary:

\- total assets checked

\- updated

\- skipped

\- failed

Project structure guidance:

Use files in locations like these unless a better fit already exists:

\- backend/app/services/metadata/exif_extractor.py

\- backend/app/services/metadata/exif_persistence.py

\- backend/scripts/run_exif_extraction.py

Implementation notes:

\- keep database session handling simple

\- use type hints

\- add docstrings

\- treat missing EXIF as normal, not as a hard error

\- do not add migration tooling yet

\- keep changes to the Asset model minimal and clear

What to explain after coding:

1\. what files were added or changed

2\. what package or external tool is required

3\. how to run the EXIF extraction script

4\. what EXIF fields are being stored

5\. how missing EXIF is handled

1\. EXIF tool choice

Use pyexiftool.

That is the preferred approach for this milestone because it should keep the code cleaner and simpler.

2\. Existing DB schema handling

Assume a fresh local DB reset for testing in this milestone.

Do not add ALTER TABLE handling yet.

Keep it simple:

\- update the Asset model

\- recreate the table/schema locally for testing

\- document the reset/init steps clearly
