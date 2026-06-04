Build Milestone 5: Metadata normalization and heuristics layer.

Goal:

Create a normalization layer that converts raw EXIF and file metadata into clean, reliable, and queryable fields.

Scope:

\- no AI models

\- no face detection

\- no CLIP

\- no cloud APIs

\- operate only on existing database records

Required behavior:

1\. Add new normalized fields to Asset model:

\- captured_at (datetime, indexed)

\- is_scan (boolean)

\- needs_date_estimation (boolean)

\- source_type (string)

2\. Timestamp normalization logic:

\- use exif_datetime_original if available

\- else use exif_create_date

\- else fallback to modified_timestamp_utc

\- store result in captured_at

3\. Scan detection:

Mark is_scan = True if:

\- camera_make or model contains known scanner brands (Epson, CanonScan, HP, etc.)

\- OR software tag indicates scanning apps (Photomyne, PhotoScan)

\- OR timestamp is clearly invalid (e.g., 2000-01-01)

If is_scan = True and no valid EXIF date:

\- set needs_date_estimation = True

4\. Source classification:

Set source_type based on metadata:

\- iphone (Apple, iPhone)

\- dslr (Canon, Nikon, Sony, etc.)

\- scan (if is_scan = True)

\- unknown otherwise

5\. Processing script:

Create a script:

\- scripts/run_metadata_normalization.py

This script should:

\- iterate over all assets

\- compute normalized fields

\- update database records

\- print summary:

total processed

scans detected

missing dates

updated records

Implementation notes:

\- keep logic simple and readable

\- do not overwrite original EXIF fields

\- only populate new normalized fields

\- safe to rerun (idempotent)

What to explain after coding:

1\. schema changes

2\. how normalization works

3\. how to run the script

4\. sample output
