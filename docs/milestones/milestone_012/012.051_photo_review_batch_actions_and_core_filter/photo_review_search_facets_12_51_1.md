# Photo Review Search and Facet Behavior — 12.51.1

## Prior Behavior (before 12.51.1)

The Photo Review search box used a token parser that routed any unrecognized input to the `camera` filter.

| Input | Parsed As | Sent to Backend |
|-------|-----------|-----------------|
| `Mary` | Camera: Mary | `camera=Mary` |
| `Disneyland` | Camera: Disneyland | `camera=Disneyland` |
| `IMG_5653` | Camera: IMG_5653 | `camera=IMG_5653` |
| `2026` | Year: 2026 | `year=2026` |
| `March` | Month: March | `month=2026-03` |

This caused all plain-text searches to silently fail with "No photos found" unless the text happened to match a camera make/model.

---

## Updated Behavior (12.51.1)

Plain text is now routed to the general `q` (filename search) parameter.  
Camera filtering requires an explicit `camera:` prefix.  
Unsupported structured prefixes are stripped and the value is treated as free text.

| Input | Parsed As | Sent to Backend |
|-------|-----------|-----------------|
| `Mary` | (free text in search box) | `q=Mary` |
| `Disneyland` | (free text in search box) | `q=Disneyland` |
| `IMG_5653` | (free text in search box) | `q=IMG_5653` |
| `camera:Canon` | Camera: Canon | `camera=Canon` |
| `camera:iPhone` | Camera: iPhone | `camera=iPhone` |
| `2026` | Year: 2026 chip | `year=2026` |
| `March` | Month: March chip | `month=2026-03` |
| `person:Mary` | stripped → free text | `q=Mary` |
| `event:Birthday` | stripped → free text | `q=Birthday` |

---

## Supported Search / Facet Syntax

### Explicit prefix (search box)

| Prefix | Maps To | Backend Param |
|--------|---------|---------------|
| `camera:<value>` | Camera chip | `camera` |

### Unambiguous implicit facets (search box)

| Input | Maps To | Backend Param |
|-------|---------|---------------|
| 4-digit year (1900–2100) | Year chip | `year` |
| Month name (January–December) | Month chip | `month` |

### Plain text (search box)

All other input → routed to `q` → searches `Asset.original_filename`.

### Dedicated UI controls (filter row, not search box)

- Year dropdown
- Month dropdown
- Visibility (Visible / Demoted / All)
- Media Type (All / Photos / Videos)
- Show Live Photo motion clips (toggle)
- Has Location (checkbox)
- Has Faces (checkbox)
- Has Unassigned Faces (checkbox)
- Undated (checkbox)

---

## Unsupported / Deferred Facets

These prefixes are parsed and stripped — value is routed to `q` (filename search) — but do **not** perform semantic filtering:

| Prefix | Status |
|--------|--------|
| `person:<value>` | Deferred — person name search not yet implemented |
| `event:<value>` | Deferred — event search not yet implemented |
| `place:<value>` | Deferred — place/location search not yet implemented |
| `source:<value>` | Deferred — source/account search not yet implemented |
| `album:<value>` | Deferred — album text search not yet implemented |
| `filename:<value>` | Equivalent to plain text (routes to `q`) |

> Note: `q` currently searches `Asset.original_filename` only. Person/event/place search is a future milestone.

---

## Search Chips

Chips appear only for explicit structured facets:

- `Year: 2026` — from year token or year dropdown
- `Month: March` — from month token or month dropdown
- `Camera: Canon` — from `camera:Canon` prefix
- `Undated` — from undated checkbox

Plain text remains visible in the search input. No chip is generated for `q` (free-text).

Chip removal clears the associated facet and reconstructs the search box text.

---

## Known Limitations

- Free-text search (`q`) matches filenames only. Searching `Mary` will return assets whose filename contains "Mary". It does not search people, places, or events.
- Camera search requires explicit `camera:` prefix. There is no dedicated camera input field (deferred to a later milestone).
- `person:Mary` currently silently falls back to `q=Mary` (filename search). A future milestone will implement person-name search.

---

## Validation Performed (12.51.1)

See Coder Response 12.51.1 for full validation details.
