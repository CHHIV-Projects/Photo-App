# Ingestion Run Status and Report Polish 12.61.8

## 1. Purpose
Milestone 12.61.8 improves Source Intake run status visibility, terminal summary clarity, and report visibility in the Ingestion tab for normal local/external operator workflows.

## 2. Active Run Panel Behavior
Implemented active run panel polish:
- status shown as explicit badge (Running, Stop Requested, etc.)
- source label/type shown
- started time shown
- stop requested signal shown when true
- key counters shown with clearer labels:
  - scanned
  - eligible unknown
  - selected for session
  - staged to Drop Zone
  - processed new unique
- Request Stop behavior preserved

## 3. Terminal Summary Behavior
Implemented terminal summary polish:
- terminal summary persists after completed/failed/stopped
- summary includes final status badge, source identity, started/finished time, and key counters
- report filename and report path shown when available
- Dismiss button added
- summary remains hidden after dismiss until a new run starts
- starting a new run resets terminal summary dismissal

## 4. Report Summary Behavior
Implemented compact report summary panel in Ingestion tab:
- View Report Summary action added from terminal panel and source detail history entries
- report detail is fetched on demand only when opened
- panel includes source identity, timing/configuration, and counters
- report filename and resolved path shown
- raw details are collapsed by default under Show raw report details
- guidance retained that full report exploration remains in Admin

## 5. Source-Specific History Behavior
Implemented source-specific recent runs in Source Profile Details drawer:
- Recent Source Intake Runs section added in existing Details drawer
- runs are filtered from existing recent report summaries by ingestion_source_id
- each entry shows timestamp, compact run outcome summary, report filename, and View Report Summary action
- fallback message for capped history limitation:
  - No recent run found in available report history.

## 6. Row-Level Last Run Behavior
Implemented compact Last Run row summary in profile table:
- Last Run column now shows compact summary based on latest matching report summary
- summary includes timestamp when available, status text, new count, failed/deferred aggregate, and source-complete indicator
- fallback behaviors:
  - Last run: no run found
  - No recent run found in available report history.

## 7. Error Display Behavior
Preserved and improved failure visibility:
- user-friendly launch failure messages remain in row/banner
- raw error details remain available in collapsible details block
- report loading errors shown inline in report summary panel

## 8. API Reuse
12.61.8 reuses existing APIs only:
- GET /api/admin/source-intake/run/status
- GET /api/admin/source-intake/reports
- GET /api/admin/source-intake/reports/{report_filename}
- POST /api/admin/source-intake/run
- POST /api/admin/source-intake/run/stop

No backend API additions were required.

## 9. Safety Boundaries
Confirmed unchanged:
- Source Intake execution semantics
- Drop Zone behavior
- Vault behavior
- provenance behavior
- iCloud/cloud orchestration flow
- staging cleanup flow
- unsupported run options

Changes are frontend-only status/report UX polish.

## 10. Validation Performed
Frontend:
- npm run build (frontend) passed

Backend regression slice:
- python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q passed (18 tests)
- python -m unittest discover -s tests -p "test_event_admin_api.py" -q passed (4 tests)

## 11. Limitations
- source-specific history is based on existing backend recent reports list (capped to recent 50)
- historical status is inferred from available data; full diagnostic depth remains in Admin
- report detail panel is intentionally compact and not a full report browser replacement

## 12. Recommended Next Milestone
Recommended next milestone:
- 12.61.9 Ingestion Tab Local/External Final Ergonomics

Potential scope:
- density/wording/layout refinements from operator feedback
- minor report readability adjustments
- row/table ergonomics after real-world usage
