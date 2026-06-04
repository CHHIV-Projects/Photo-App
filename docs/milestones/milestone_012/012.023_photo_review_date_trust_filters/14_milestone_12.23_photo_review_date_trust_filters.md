# Pre-Work Questions — Existing Timeline / Time Trust / Undated Logic

Before we define a new Undated Asset Discovery milestone, please inspect the existing timeline and capture-time trust implementation so we do not duplicate prior work.

## 1. Existing Time Trust Model

Please identify:

- where capture time trust is stored
- exact field name(s)
- allowed values
- where values are assigned
- whether values are `high`, `low`, `unknown` or similar

Please confirm whether this was introduced around Milestone 11.9.

---

## 2. Existing Undated / Unknown Logic

Please identify how the system currently represents assets with missing or unreliable capture dates.

Specifically:

- What does `unknown` mean today?
- Is `unknown` equivalent to `captured_at IS NULL`?
- Or does it mean captured_at exists but is not trusted?
- How are imported/download-date timestamps classified?
- Are scan/unknown capture types handled separately?

---

## 3. Timeline UI Behavior

Please inspect the current Timeline UI logic shown in the screenshot.

Please identify:

- where the Trust Filter is implemented
- how High / Low / Unknown filtering works
- how the bucket counts H / L / U are calculated
- whether unknown-date assets appear in timeline buckets
- whether assets with `captured_at IS NULL` appear anywhere

---

## 4. API / Backend Endpoints

Please identify the backend endpoints and query parameters used for:

- timeline bucket generation
- trust filtering
- year/month filtering
- high/low/unknown counts

Please include relevant files/functions.

---

## 5. Photo Review Integration

Please determine whether Photo Review already supports:

- trust filtering
- unknown-date filtering
- `captured_at IS NULL` filtering
- low-trust date filtering

If not, identify what minimal backend/frontend changes would expose existing trust logic there.

---

## 6. Current Gaps

Please summarize what is already implemented versus what is missing.

Specifically, answer:

- Can the user already find all unknown-date assets somewhere?
- Can the user find all assets where `captured_at IS NULL`?
- Can the user find low-trust assets?
- Is the current UI sufficient, or is it only available in the older Timeline workspace?
- Is Photo Review missing this capability?

---

## 7. Recommended Minimal Milestone

Based on the above, please recommend whether the next milestone should be:

A. New Undated Asset Discovery system  
B. Integration of existing time-trust filters into Photo Review  
C. Cleanup/refinement of Timeline trust filtering  
D. Admin/data-quality report for missing/low-trust dates

Please do not implement yet. Return findings and recommended scope only.



## Coder Pre-work Response

Q1 — Time Trust Model
Field: Asset.capture_time_trust — String(32), default "unknown". See asset.py:47.
Override field: Asset.capture_time_trust_override — nullable, allows manual correction. See asset.py:49.
Allowed values: "high", "low", "unknown".
Where assigned: classify_asset_capture_type() in metadata_normalizer.py:139. Rules:
"high" → capture_type is digital AND valid EXIF date exists
"low" → scan, invalid timestamp, or no valid EXIF date
"unknown" → all other / unclassifiable
Effective value: always resolved via coalesce(capture_time_trust_override, capture_time_trust, "unknown"), so the override wins. See timeline_service.py:30.
Likely introduced around Milestone 11.9 — consistent with the metadata normalization phase.
Q2 — Undated / Unknown Logic
unknown ≠ captured_at IS NULL.
captured_at is always populated during metadata normalization — the normalizer falls back to modified_timestamp_utc if no EXIF date exists. See _choose_captured_at() in metadata_normalizer.py:102. There is no code path that leaves captured_at as NULL for ingested assets.
unknown trust means the timestamp came from a fallback source (filesystem mod date), not from camera EXIF.
low trust means a scan marker was detected, or the EXIF timestamp was invalid (e.g., 2000-01-01 placeholder).
Import/download timestamps that fall through to modified_timestamp_utc will be classified unknown or low, not high.
captured_at IS NULL therefore should theoretically never occur for a normally ingested asset. The undated filter in the API (?undated=true) returns captured_at IS NULL rows, which would only exist if an asset was persisted without running normalization.
Q3 — Timeline UI Behavior
Trust filter is implemented entirely in TimelineView.tsx:24 — state variable selectedTrusts, defaults to all three values (all-inclusive).
High / Low / Unknown toggles call handleToggleTrust(), which updates selectedTrusts. When all three are selected the parameter is omitted (no filter); when a subset is selected, trust[] is sent as a query param.
H / L / U bucket counts come from high_trust_count, low_trust_count, unknown_trust_count per bucket — computed server-side in get_timeline_summary(). See timeline_service.py:33.
Unknown-date assets (captured_at IS NULL) can appear in an undated bucket — the timeline summary response has an undated_bucket field in the type. However, based on Q2, there should be no such assets in practice.
Assets with captured_at IS NULL do not appear in dated timeline buckets.
Q4 — API Endpoints
Purpose    Endpoint    Key params
Timeline bucket generation    GET /api/timeline/summary    decade, year, month, trust[], undated
Trust filtering    GET /api/photos    trust[] multi-value
Undated filtering    GET /api/photos    undated=true
Year/month/date filtering    GET /api/photos    year, month, date
H/L/U counts per bucket    GET /api/timeline/summary    returns high_trust_count, low_trust_count, unknown_trust_count
All filtering routes through apply_asset_time_filters() and TimelineFilter dataclass in timeline_service.py.

Q5 — Photo Review Integration
Photo Review (PhotosView) does not have trust or undated filtering controls. The component's Props interface accepts searchQuery, cameraQuery, startDate, endDate, sortBy — but no trust or undated. See PhotosView.tsx:35.

The backend already supports ?trust[] and ?undated=true on GET /api/photos. The gap is entirely in the frontend — no filter UI and no passing of trust params from Photo Review.

capture_time_trust is displayed read-only in the photo detail panel (the metadata row), so the value is visible per-photo, but there is no way to filter by it from Photo Review.

Q6 — Current Gaps
Capability    Available    Where
Find all unknown-trust assets    ✅    Timeline — deselect High + Low, leave Unknown
Find all low-trust assets    ✅    Timeline — deselect High + Unknown, leave Low
Find assets with captured_at IS NULL    ✅ (backend)    No UI — ?undated=true works but no button exists in Timeline or Photo Review
Trust filter in Photo Review    ❌    Not implemented
Undated filter in Photo Review    ❌    Not implemented
See trust per photo    ✅    Photo detail metadata panel
Q7 — Recommendation
Option B — Integration of existing time-trust filters into Photo Review.

All backend infrastructure is already complete. The work is a focused frontend addition: expose trust[] and undated filter controls in the Photo Review view, pass them through to getPhotos(), and wire them into the existing component state. No backend changes needed. This is the lowest-risk, highest-value path — a user can currently only access trust filtering through the Timeline workspace.

Option A (new Undated Discovery system) would be premature since captured_at IS NULL assets don't exist in practice. Option D (data quality report) is lower priority unless you want to surface low-trust counts in Admin.





Milestone 12.23 — Photo Review Date Trust Filters
Coder-ready prompt
# Milestone 12.23 — Photo Review Date Trust Filters## GoalExpose the existing capture-time trust filtering system inside Photo Review so users can find and review photos with high, low, or unknown date trust.This milestone reuses the existing backend time-trust model and API filters. It should not create a new undated/date system.---## ContextThe system already has a capture-time trust model:```textcapture_time_trust = high | low | unknowncapture_time_trust_override = optional manual override
Effective trust is resolved as:
capture_time_trust_override > capture_time_trust > unknown
The Timeline workspace already supports trust filtering and shows H / L / U bucket counts.
The backend already supports time-trust filtering through:
GET /api/photos?trust[]=highGET /api/photos?trust[]=lowGET /api/photos?trust[]=unknown
The backend also supports:
GET /api/photos?undated=true
However, undated=true means captured_at IS NULL, which should be rare because normal metadata normalization falls back to filesystem modified time.
The current gap is frontend integration: Photo Review does not expose trust filters.

Core Principle

Reuse the existing time-trust model. Do not recreate date/undated logic.


Scope
In Scope


Add High / Low / Unknown trust filter controls to Photo Review


Pass selected trust values to the existing photos API


Integrate trust filters with existing Photo Review filters/search behavior


Preserve existing Timeline trust behavior


Optionally expose an “Undated Only” filter for captured_at IS NULL


Ensure active filters are visible to the user


Out of Scope


backend metadata model changes


new date inference logic


OCR/date inference


manual date editing


batch metadata correction


changing metadata normalization fallback behavior


changing Timeline filter behavior


adding Admin data-quality dashboard



Required Behavior
1. Trust Filter Controls
Photo Review should allow filtering by:
HighLowUnknown
Behavior should match Timeline semantics:


all selected = no trust filter sent


subset selected = send selected trust values


none selected should either be prevented or treated as all selected


Preferred UI:
Date Trust:[High] [Low] [Unknown]

2. Backend API Usage
Use the existing GET /api/photos trust query support.
Do not add a new endpoint unless coder discovers current API wiring is incomplete.
Expected query examples:
/api/photos?trust=unknown/api/photos?trust=low/api/photos?trust=high&trust=unknown
Use existing project query parameter convention.

3. Undated Filter
Add only if low-risk.
Label clearly as:
Undated
Meaning:
captured_at IS NULL
Do not confuse this with unknown trust.
Preferred UI note or naming:
Undated (rare / missing captured_at)
If UI space is limited, defer Undated and focus on trust filters.

4. Active Filter Visibility
If Photo Review has filter chips or active filter display, include:


Trust: High


Trust: Low


Trust: Unknown


Undated, if enabled


User should be able to tell when trust filtering is active.

5. Preserve Existing Behavior
Do not break:


unified search


year/month/date filtering


camera filtering


person filtering


place filtering


visibility/demoted filtering


pagination/sorting


Trust filters should compose with existing Photo Review filters.

Frontend Requirements
Update Photo Review / PhotosView integration as needed.
Likely areas:


Photo Review parent state


PhotosView props


API client getPhotos()


active filter chips


filter UI controls


Coder should confirm exact component ownership before coding.

Backend Requirements
No backend changes expected.
Coder should verify:


GET /api/photos supports trust[]


GET /api/photos supports undated=true


API client can send multi-value trust params correctly


Only make backend changes if existing support is incomplete or broken.

Validation Checklist
Trust Filtering


High-only filter returns high-trust assets


Low-only filter returns low-trust assets


Unknown-only filter returns unknown-trust assets


High + Unknown returns both


All selected behaves like no trust filter


Composition
Trust filters work together with:


search


year/month/date


person filters


place filters


visibility filters


UI


trust filter state is visible


filters can be toggled/reset


Photo Review still loads normally


Timeline behavior unchanged


Undated, if implemented


Undated filter calls existing undated=true


It is clearly distinct from Unknown trust


Empty results are handled gracefully



Definition of Done
Milestone 12.23 is complete when:


Photo Review exposes existing date-trust filtering


user can find unknown-trust and low-trust assets from Photo Review


filters compose with existing Photo Review controls


no duplicate date/undated logic is introduced


Timeline trust filtering remains unchanged


This is the right next step: small, useful, and grounded in the system you already built.