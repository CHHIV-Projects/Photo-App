**Milestone 11.9 — Timeline and Time Layer**

**Goal**

Make time a **first-class navigation and filtering layer** across the archive, allowing the user to browse and inspect photos by:

-   year
-   month
-   decade
-   exact date
-   capture-time trust

This milestone turns time from passive metadata into an active organizational surface.

**Context**

The current system already supports:

-   metadata extraction and normalization
-   capture-type classification
-   capture-time trust (high \| low \| unknown)
-   event grouping based on trusted timestamps
-   Photos, Events, Places, People, Review, and Unassigned Faces views
-   photo detail metadata display

Current limitation:

-   time exists in metadata and affects event grouping, but there is no dedicated time-based browsing layer
-   user cannot navigate the archive naturally by year/month/decade or inspect trust distribution across time

This milestone introduces a **timeline/time-layer capability** without overreaching into full event editing or advanced analytics.

**Scope**

**In Scope**

-   backend time aggregation and filtering APIs
-   timeline-oriented navigation model
-   browsing by:
    -   decade
    -   year
    -   month
    -   exact date
-   capture-time trust filtering
-   timeline/time metadata display in UI
-   integration with Photos and/or Events browsing where appropriate

**Out of Scope**

-   event editing
-   manual event creation
-   event stability refactor
-   collections/albums (11.10)
-   person suggestion engine (11.11)
-   semantic or natural-language time search
-   advanced charts/analytics
-   calendar-style editing UI

**Product Intent**

The user should be able to answer questions like:

-   “Show me photos from the 1990s”
-   “What do I have from 2004?”
-   “Show me March 2012”
-   “Show only high-trust dated photos”
-   “Help me understand where my archive has unknown or low-trust time data”

The time layer should support both:

-   **navigation**
-   **confidence-aware browsing**

**Functional Requirements**

**1. Time Aggregation Model**

Add backend support for timeline aggregation based on normalized capture date data.

Required rollups:

-   by decade
-   by year
-   by month
-   by exact date

Each aggregation should provide counts of assets.

Capture-time trust must be available alongside counts, at minimum:

-   total assets
-   high-trust count
-   low-trust count
-   unknown-trust count

**2. Time Filtering**

Support filtering assets by:

-   decade
-   year
-   month
-   exact date
-   capture-time trust

Filters should be combinable where sensible, for example:

-   year = 2012 + trust = high
-   decade = 1990s + trust in (high, low)

Do not overdesign query semantics. Keep them simple and explicit.

**3. Date Source Rules**

Use the existing normalized metadata model and trust rules already established in 11.6.

Important:

-   The timeline must reflect **stored normalized capture date/time values**
-   Do not invent alternate date inference in this milestone
-   Low/unknown trust assets may still appear in the time layer if they have date values, but their trust must be visible
-   Assets with no usable normalized date should not be silently misrepresented

If necessary:

-   include an “undated / no usable date” bucket

This is preferred if simple.

**4. Decade / Year / Month Navigation**

Expose a navigation structure that allows progression:

-   decade → year → month → photo results

Minimum expectation:

-   user can browse years and months from a selected parent period
-   user can retrieve matching photos for that period

Exact UI form can stay simple:

-   sidebar
-   summary panels
-   list/grid sections
-   expandable sections

Do not overcomplicate the first version.

**5. Trust-Aware Timeline Display**

Time browsing must surface capture-time trust clearly.

Examples:

-   count badges by trust level
-   filter chip/toggle for trust
-   visible label on time buckets
-   photo-level trust indicator in results if already available

Goal:

-   user can distinguish reliable timeline areas from uncertain ones

**6. Photos Integration**

Integrate timeline filtering with existing photo browsing.

At minimum:

-   user can request photos for a selected decade/year/month/date
-   photo results reflect selected time filter
-   trust filter can refine results

This can reuse current Photos view/filter patterns where practical.

**7. API Design**

Provide backend endpoints or endpoint extensions for:

**A. Timeline Summary**

Returns aggregated counts by period.

Suggested capability:

-   top-level decades
-   drill-down into years for a decade
-   drill-down into months for a year
-   optional undated bucket

**B. Time-Filtered Photo Query**

Returns photo results for selected time period and optional trust filter.

Keep API simple and explicit.  
Do not introduce a generic analytics framework.

**8. UI Design Requirements**

Keep UI scope moderate.

Recommended approach:

-   add a **Timeline view** or a **Time layer section** integrated into existing browsing
-   show:
    -   time buckets
    -   asset counts
    -   trust distribution
-   allow clicking/drilling into period results

UI should prioritize:

-   readability
-   confidence visibility
-   low cognitive load

Do not attempt a full visual charting system unless already trivially supported.

**9. Undated / Uncertain Assets**

Decide a clear handling strategy for assets lacking usable timeline placement.

Preferred behavior:

-   provide an **Undated** or **No usable date** bucket
-   allow user to inspect those assets separately

This is important because unknown/low-trust date handling is a core part of the architecture.

**Backend Requirements**

**Services**

Add time aggregation / query support using normalized asset metadata.

**Data Rules**

Use existing normalized date/trust fields as source of truth.

**API**

Add timeline-focused endpoints or extend existing filtering APIs as needed.

**Performance**

Design queries to remain practical for medium archive sizes.  
Do not prematurely optimize, but avoid obviously inefficient full in-memory scans if DB aggregation is straightforward.

**Frontend Requirements**

**Time Navigation**

Provide a user-facing time browsing surface with:

-   decade
-   year
-   month
-   optional undated bucket

**Result Integration**

Selecting a time bucket should show matching photos and relevant counts.

**Trust Visibility**

Show trust in the UI in a simple, readable way.

**Existing View Stability**

Do not break current Photos / Events / People / Review flows.

**Validation Checklist**

**Data / API**

-   timeline summary returns correct counts by decade/year/month/date
-   trust counts are correct
-   undated/no-usable-date assets handled clearly
-   time filters return correct assets

**UI**

-   user can browse decade → year → month
-   selecting a period shows matching photo results
-   trust state is clearly visible
-   undated assets are accessible if implemented

**Regression**

-   existing photo browsing still works
-   event system remains stable
-   capture-type / trust metadata display remains correct

**Usability**

-   timeline browsing feels understandable and useful
-   low-trust and unknown-trust dates are not misleadingly presented as equally reliable

**Deliverables**

-   backend time aggregation/query implementation
-   API support for timeline browsing
-   frontend timeline/time-layer UI
-   code summary describing:
    -   aggregation model
    -   filter model
    -   trust handling
    -   undated handling
-   validation results from coder

**Definition of Done**

-   user can browse the archive by decade, year, and month
-   user can filter photos by time period and capture-time trust
-   trust-aware time browsing is visible and understandable
-   undated or unusable-date assets are handled clearly
-   existing system behavior remains stable

11.9 decisions:

- Use a dedicated top-level Timeline view
- Exact date bucketing = stored captured_at date component as-is
- No UTC/day reinterpretation
- Undated bucket = only assets where captured_at IS NULL
- Assets with low/unknown trust but a stored date still appear in timeline buckets
- Extend existing photos list API with explicit params: decade, year, month, date, trust
- Use one timeline summary endpoint with drill-down params:
  - top level = decades
  - ?decade=1990 -> years
  - ?year=2004 -> months
  - optional ?month=2004-03 -> days