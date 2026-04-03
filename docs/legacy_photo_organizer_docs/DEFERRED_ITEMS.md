# Deferred Implementation Items

This document tracks features and design decisions that were intentionally deferred for later phases.

## Video Handling Strategy
**Status**: Deferred (Phase 2)
**Reason**: Complex end-to-end workflow; prioritizing photos-only ingestion first for stability.
**Scope when ready**:
- iCloud video metadata enumeration
- Batch download with resume for large video files
- Video keyframe/thumbnail extraction
- AI model support (clip, deepface on video)
- UI playback and search capabilities
- Indexing strategy for video-heavy libraries

## Sidecar File Handling (.aae, .xmp)
**Status**: Deferred (Phase 2)
**Reason**: Photos-only pipeline does not require sidecars initially; testing mode accepts loss of Apple edit metadata.
**Scope when ready**:
- Detection and preservation of Apple edit instruction files (.aae)
- XMP metadata sidecar handling
- Policy decision: preserve sidecars in vault, archive separately, or ignore
- Edited rendition preference logic (original vs. edited photo export from iCloud)
- Forensic traceability for edit history

## Known Gaps (Current Phase)
- No heuristic dedupe (filename + size + date) — using strict source-ID dedupe only
- No merged duplicate detection across iCloud/local/OneDrive/GDrive — dedup handled per-source for now
- No automatic scheduler setup (manual triggers only; scheduler wrapper added later)
