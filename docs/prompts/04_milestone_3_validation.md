Build the next small verification step: database read/check script.

Goal:

Create a simple script that reads Asset records from PostgreSQL and prints a small sample so we can verify stored data, including EXIF fields.

Scope:

\- read only

\- no inserts

\- no updates

\- no deletes

\- no API endpoints

\- no frontend work

\- keep it simple and beginner-friendly

Required behavior:

1\. Connect to PostgreSQL using the existing SQLAlchemy session setup.

2\. Query Asset rows from the database.

3\. Print a small readable sample of records.

4\. Include fields such as:

\- sha256

\- vault_path

\- original_filename

\- original_source_path

\- extension

\- size_bytes

\- modified_timestamp_utc

\- exif_datetime_original

\- exif_create_date

\- gps_latitude

\- gps_longitude

\- camera_make

\- camera_model

\- lens_model

5\. Support an optional limit argument, defaulting to something small like 5 or 10.

6\. Print a short summary count of total assets in the table.

Project structure guidance:

Create a script like:

\- backend/scripts/check_assets_in_db.py

Implementation notes:

\- keep code minimal

\- use the existing Asset model

\- use the existing SessionLocal

\- output can be JSON or a readable text summary

\- do not add filtering features yet unless very simple

\- do not add API routes

What to explain after coding:

1\. where the script lives

2\. how to run it

3\. what the output shows
