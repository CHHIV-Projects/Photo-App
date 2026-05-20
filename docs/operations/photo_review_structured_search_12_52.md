# Photo Review Structured Search & Facets — 12.52

## Supported Facets

### Filename (Free-Text Search)

Label: **Filename contains**

Searches `Asset.original_filename` using LIKE (case-insensitive).

Backend param: `q`

### Date (Year & Month)

Dropdowns for:
- Year (1900–2100)
- Month (January–December, disabled if year not selected)

Backend params: `year`, `month`

### People

Label: **People (select by name)**

People are selected by `Person.display_name` in the UI and resolved to backend `person_ids` internally.

Multiple selected people use **AND semantics**.

Example:
```
People: Mary, Charlie
=> assets containing both Mary AND Charlie
```

Backend param: `person_ids`

### Album / Collection

Label: **Album**

- Single album selection
- Dropdown populated from existing `/api/albums` endpoint

Backend param: `album_id`

### Event

Label: **Event**

- Single event selection
- Dropdown populated from existing `/api/events` endpoint
- Uses event label when present, fallback to `Event #{id}`

Backend param: `event_id`

### Place / Location

Label: **Place contains**

Searches place-related fields:
- `user_label`
- `formatted_address`
- `city`
- `state`
- `country`

Backend param: `place_query`

### Provenance / Source / Folder

Label: **Source / Folder contains**

Searches across provenance/source fields:
- `source_label`
- `source_type`
- `source_relative_path`
- `source_root_path`
- `source_path`

Backend param: `provenance_query`

## UI Controls Summary

| Control | Type | Behavior |
|---------|------|----------|
| Filename contains | Text input | LIKE search on Asset.original_filename |
| Year | Dropdown | Exact year filter, 1900–2100 |
| Month | Dropdown | Exact month filter (requires year) |
| Visibility | Dropdown | Visible / Demoted / All |
| Media Type | Dropdown | All / Photos / Videos |
| People | Name picker (search + select + chips) | AND filter for multiple people |
| Album | Dropdown | Single album selection |
| Event | Dropdown | Single event selection |
| Place contains | Text input | LIKE search on place fields |
| Source / Folder contains | Text input | LIKE search on provenance fields |
| Show Live Photo motion clips | Checkbox | Include/exclude motion pairs |
| Has Location | Checkbox | Filter by presence of GPS |
| Has Faces | Checkbox | Filter by presence of faces |
| Has Unassigned Faces | Checkbox | Filter by unassigned face count |
| Undated | Checkbox | Filter by missing date |

## Filter Interaction

- Active filters combine with AND semantics across facets
- Selected people combine with AND semantics within the People facet
- Selection clears when filters change

## Deferred / Known Limitations

1. Person aliases are deferred. Current People picker matches `display_name` only.
2. Filename search does not include person/event names; use dedicated facet controls.
3. Place control is free-text only; no autosuggest UI yet.
4. Provenance control is free-text only; no path tree browser yet.

## Future Enhancements

- Add person alias support in a person/face workflow milestone
- Add autosuggest for people and places
- Add optional full-text metadata search beyond filename
