# Coder Response 12.45.2

## 0. Review Scope

Reviewed the full requirements document, not only the coder-question section.

Primary evidence sources used:
- current backend/frontend code
- admin/source-intake/iCloud-acquisition/iCloud-cleanup services and APIs
- models/schemas/startup wiring
- UI components for Photo Review, Workbench, and Admin

This is a technical gap analysis only (no implementation changes).

---

## 1. Requirements Status Classification

## 1.1 Already Satisfied (or close to satisfied)

- Source Intake run controls and status tracking exist.
- Source Registry exists, including `account_username` on sources.
- iCloud acquisition via `icloudpd` exists with run/status/stop and report output.
- iCloud staging cleanup exists with dry-run + execute and conservative eligibility checks.
- Non-destructive architecture is strongly enforced (Vault immutability pattern, staging-only cleanup).
- Exact dedupe (SHA-256) and provenance tracking are active.
- Live Photo pairing pipeline exists, including icloudpd naming support.
- Video metadata trust model exists for MOV/MP4/M4V extraction/classification.
- Admin cards for duplicate processing, face processing, place geocoding, preview generation, live photo pairing, source intake, iCloud acquisition, and cleanup are present.
- Duplicate Groups and Duplicate Suggestions have pagination.
- Face Review has previous/next cluster navigation.
- Base album CRUD and asset membership are implemented (using `collections`/`collection_assets` tables under album APIs).

## 1.2 Partially Satisfied

- Production start/stop experience: runnable manually, but no production launcher shell/packaging.
- Deployment separation: config supports env vars, but no formal dev/prod profiles and promotion tooling.
- Clean DB init: schema ensure exists, but no single production bootstrap command/checklist.
- iCloud non-repeat strategy: fixed-window recent acquisition is implemented; true checkpoint/until-found strategy is not.
- HEIC preview pathing: central mechanism exists (`display_preview_path` + `_build_asset_url`), but not consistently used on all API surfaces.
- Workbench naming/layout: functional but still development-oriented labels and layout density.
- Photo Review as primary workspace: strong foundation, but missing requested multi-select batch actions and broader facets.
- Admin run visibility: latest status is visible, but unified acquisition/intake/cleanup history is not.

## 1.3 Not Implemented / Clearly Missing

- One-click production launcher with minimized console UX.
- Formal production release packaging process and artifact pruning automation.
- Unified Collections model above albums/events as described in requirements (current "albums" are backed by `collections`, but no event-linking/live-reference model).
- Event <-> Album integration model.
- Unified acquisition + intake + cleanup workflow history view.
- Full v1 facet set in search/filter (person/album/collection/event/place-label/provenance/media-type/demotion together).
- Multi-select batch operations in Photo Review for album/collection/event actions.
- Live Photo motion companion hide/filter controls in browsing surfaces.
- Dedicated Admin Ingestion tab and bounded/paginated source table UX.

---

## 2. Likely Implementation Tracks

- Track A: Production runtime/launcher and environment separation.
- Track B: Production DB bootstrap + release packaging/cleanup tooling.
- Track C: iCloud non-repeat acquisition strategy (until-found/checkpoint).
- Track D: Display preview URL consistency pass across all API surfaces.
- Track E: Workbench naming/layout cleanup and bounded lists.
- Track F: Photo Review batch action framework + facet expansion.
- Track G: Organization model completion (Collections with album/event links and resolved dedupe).
- Track H: Unified operational history and ingestion workflow UX in Admin.

---

## 3. Technical Risks

- iCloud repeat-download behavior after staging cleanup can produce operator friction and unnecessary bandwidth/IO.
- Current "album" implementation already maps to `collections` tables, creating semantic debt when true Collections are introduced.
- HEIC preview inconsistency likely persists where API responses build URLs without passing `display_preview_path`.
- Production release contamination risk is high without explicit packaging/artifact filtering.
- Event/album/collection integration may become a larger data-model migration than it appears.
- NAS behavior and permissions differ from Windows; runtime assumptions need explicit validation under target NAS paths.

---

## 4. Missing Technical Details Blocking Final Scope Precision

- Final production host model (single machine vs split NAS/server + UI host).
- Required "launcher UX" level (script shortcut vs packaged desktop shell).
- Backup/restore RPO/RTO and operational runbook expectations.
- Whether v1 requires true until-found semantics or acceptable checkpoint approximation.
- Exact collections semantics for event links and conflict resolution.
- Performance targets (ingestion throughput, UI latency, max dataset assumptions).

---

## 5. Suggested Milestone Breakdown

1. 12.45.3 Deployment Baseline: env profiles, start/stop scripts, health checks.
2. 12.45.4 Clean Production Bootstrap: DB init/migrate command, source seed flow, release package spec.
3. 12.45.5 iCloud Non-Repeat: until-found/checkpoint design + implementation + reports.
4. 12.45.6 Display Consistency: centralized image URL contract audit/fix across APIs.
5. 12.45.7 Workbench Naming/Layout: Review->Face Review, Photos->Photo Detail, width/list UX.
6. 12.45.8 Photo Review Batch Ops: multi-select + add-to album/event/collection + demotion batch.
7. 12.45.9 Organization Model Completion: event-album integration + true collections linking.
8. 12.45.10 Admin Ingestion UX + Unified History.
9. 12.45.11 Production Trial Runbook: clean ingest of representative production batch.

---

## 6. Architecture Conflicts / Ambiguities

- Naming conflict: "Albums" currently persist to `collections`/`collection_assets`; future Collections as a higher layer conflicts with current schema semantics.
- API/UI naming drift: requirements define Photo Detail and Face Review, code still uses `photos` and `review` view modes.
- Preview contract drift: some services call `_build_asset_url` without preview path context, weakening central HEIC strategy.

---

## 7. Design-First Milestones Recommended

- iCloud non-repeat strategy (until-found vs checkpoint) should be design-first.
- Collections + event/album linking should be design-first (data model and resolved-membership semantics).
- Unified ingestion history should be design-first (cross-run correlation model).
- Production launcher/packaging should be design-first (ops constraints, host topology, startup policy).

---

## 8. Items Larger Than They Appear

- Collections (if implemented as true aggregate of direct assets + linked albums + linked events + resolved dedupe).
- Unified search/filter facet expansion across provenance/organization models.
- Production packaging and clean workspace separation in a historically milestone-heavy repo.
- iCloud non-repeat behavior with correctness and operator clarity.

---

## 9. Explicit Answers to Coder Review Questions

## Deployment / NAS

1. Backend/frontend/docker/browser startup now: Docker services started separately; backend via uvicorn; frontend via Next dev/start; browser opened manually to local URL.
2. Clean production launcher needs: orchestrated start order, readiness checks, browser open, graceful stop, logs routing, and env profile selection.
3. Hardcoded/dev-specific areas: localhost CORS defaults, relative storage defaults, hardcoded helper path defaults (`.tools/icloudpd`), development tab labels and milestone text, local URL assumptions.
4. NAS-backed Vault reliability needs: configurable absolute paths, permission model validation, IO retry/error policy, backup/snapshot integration, and path-health checks.
5. Production-required vs dev/test scripts: runtime requires app code, docker compose, startup scripts, schema/init path, operator docs. Most `backend/scripts/*` utility/debug/migration scripts remain dev/operator maintenance artifacts unless explicitly promoted.

## Clean DB / Workspace

6. Clean production DB init now: create empty DB + run app startup schema ensures + optional explicit bootstrap script; then register only production sources.
7. Schema ensure/migrations required: yes, startup calls multiple `ensure_*_schema` functions; these must run before first use.
8. Runtime-required folders/files: backend app code, frontend build/runtime, docker config, env files, storage dirs (`vault`, `drop_zone`, `exports/icloud`, `logs`, `previews`, `review`, `quarantine`) and runtime reports.
9. Test/experimental/historical artifacts: milestone prompts, coder responses, many one-off scripts, debug files, trial exports/logs, and experimental adapters.
10. Recommended cleanup/release process: scripted release manifest + copy/package only runtime assets + explicit denylist for docs/prompts/debug/test outputs.

## Ingestion

11. Local ingestion status for large folders: batching and source limits are implemented; deterministic skip-known by source-relative provenance exists; operationally viable but needs production-scale throughput validation.
12. iCloud acquisition/intake status: implemented end-to-end (acquire -> staged export -> Source Intake -> optional cleanup) with admin controls and reports.
13. Needed for non-repeat until-found: persist checkpoint/known boundary and integrate acquisition stop logic beyond fixed recent window.
14. Can `icloudpd --until-found` satisfy requirement: potentially yes if supported in deployed version/workflow; current code does not use it yet and needs design/integration/testing.
15. Risks of fixed-window after cleanup: repeated downloads, operator confusion, extra IO/bandwidth, and false impression of "new" work.

## Media Display

16. Where images render today: Photo Review, Photo Detail(Photos), Places, Albums, Events, Duplicate Groups, Duplicate Suggestions, Presentation Viewer, Face Review and Unassigned Faces.
17. Surfaces likely not consistently using display preview contract: Albums and Places APIs build raw asset URLs without passing `display_preview_path`; event/detail lists should be audited similarly.
18. Best central HEIC fix: enforce one backend image-url builder contract returning preview URL when available, and ensure every list/detail service uses it with preview-path context.
19. Larger duplicate review previews need: CSS/layout updates plus optional modal/presentation open path directly from duplicate cards.
20. Hide/filter live motion companions needs: query-level filter flags + UI toggles in Photo Review and related lists.

## UI / Workbench

21. Rename Review -> Face Review: update nav labels/view enum text and related component headings.
22. Rename Photos -> Photo Detail: update nav labels, route/view names, and API client naming where user-facing.
23. Improve width/layout globally: adjust shell/container max-width constraints and panel/grid CSS across core views.
24. Pagination/next for face clusters: previous/next exists in detail; list endpoint already supports offset/limit but UI list needs paged controls or infinite scroll.
25. Unassigned Faces create-cluster behavior fix: ensure post-create refresh preserves context and gives deterministic success feedback; current refresh exists but UX bug should be reproduced and patched with explicit state transitions.

## Photo Review

26. Existing search/filter: year/month/date trust, camera, has_location, has_faces, has_unassigned_faces, canonical-first sort, timeline summaries.
27. Missing requested facets: person, album, collection, event label, place label/geography detail, provenance/source, media type, demotion toggle in primary filter UX.
28. Multi-select actions require: selection model, bulk action APIs, optimistic UI, conflict/result reporting.
29. Presentation-mode-on-click requires: click binding from tile image to existing PresentationViewer flow and focus/return behavior.
30. Batch add to album/collection/event requires: bulk membership/assignment APIs and integrated UI action drawers.

## Organization Model

31. Current Album/Event/Place state: albums CRUD and membership exist (backed by `collections` tables), events exist with labeling/merge/assignment, places listing/detail/edit label exists.
32. Event <-> Album integration needs: link model/table(s), API endpoints, UI workflows, and conflict rules.
33. Collections as first-class model needs: dedicated collection API/service/UI separate from album semantics plus linked album/event references.
34. Collections schema likely needs: `collections`, direct asset link table, linked album table, linked event table, resolved-membership query strategy.
35. Live album/event references need: link tables + resolver that expands current members at query time.
36. Resolved collection dedupe: deterministic dedupe by `asset_sha256` over union(direct assets, linked album assets, linked event assets).

## Search / Metadata / Tags

37. Deterministic metadata/provenance facets already exist: capture date/time trust, camera make/model, location presence, face counts, duplicate/canonical/visibility, provenance detail in photo detail.
38. Search today: filename/camera/date range + timeline filters + has location/faces/unassigned + sort/paging.
39. Needed for EXIF/provenance facets: extend search query builder and indexes for source label/path/media type/event/album/collection/place label and trust facets.
40. Tags storage recommendation: both. Keep deterministic derived facets as primary v1 search mechanism; add user-managed tags only if minimal schema/API/UI can be delivered safely.

## Admin / Operations

41. Existing admin cards: summary, duplicate processing, place geocoding, face processing, HEIC preview generation, live photo pairing, iCloud acquisition, source intake/source registry, iCloud staging cleanup.
42. Dedicated Ingestion tab needs: admin layout refactor into subsections/tabs combining source registry, acquisition, intake, cleanup, and run outcomes.
43. Source lists needing bounds: source registry/source-intake source lists and report/history tables should have pagination/virtualization and bounded container heights.
44. Run history/report visibility today: source intake report list/detail exists; iCloud acquisition and cleanup expose latest/current status with report path but no robust unified history UI.
45. Unified acquisition/intake/cleanup history needs: normalized run-history model (run type, source, timestamps, status, report path, correlation IDs) + cross-workflow timeline UI.

---

## 10. Quick Wins vs Large Architecture Work

## Quick Wins

- Rename nav labels (`Review` -> `Face Review`, `Photos` -> `Photo Detail`).
- Add paged cluster list controls using existing offset/limit API.
- Centralize image URL generation and patch Albums/Places/Event surfaces.
- Add Admin bounded tables/scroll areas.
- Add Photo Review click-to-presentation binding.

## Large Work

- Non-repeat iCloud strategy (until-found/checkpoint) with operator-safe behavior.
- True Collections model with live album/event references.
- Unified run history across acquisition/intake/cleanup.
- Production packaging/launcher/release promotion flow.

---

## 11. Insights

- The codebase has strong operational primitives already; v1 risk is now mostly workflow cohesion and release discipline.
- The largest hidden complexity is model semantics around Albums vs Collections and cross-linking with Events.
- A centralized "image URL contract" is the highest leverage media-display fix for v1 reliability.
- Production readiness is now less about new AI features and more about operational correctness and packaging.

---

## 12. Specific Questions Back to Product/Owner

1. For v1, is a scripted launcher (with browser auto-open and clean stop script) acceptable, or is a packaged desktop shell required?
2. Should Collections v1 include event and album links immediately, or can v1 ship with direct-photo collections plus one link type first?
3. For iCloud non-repeat, is "recent + checkpoint + known-threshold stop" acceptable if `--until-found` proves unreliable in some environments?
4. Should source-level cleanup/report history be retained indefinitely in DB, or rolled/pruned on policy?
5. Is Photo Review expected to be the only place for batch organization actions in v1, or can Album/Event pages keep some overlapping actions?
6. Is there a strict target for production-scale validation (asset count, run duration, storage footprint) that must pass before v1 sign-off?
7. Should we formally treat current "albums" storage tables as legacy and migrate to a new explicit collection schema, or keep current tables and rebrand behaviorally?
8. Do you want hard separation into two workspaces now (dev and prod), or one repo with profile-based runtime separation for v1 launch?
