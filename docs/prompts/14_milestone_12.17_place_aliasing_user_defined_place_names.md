# Milestone 12.17 — Place Aliasing / User-Defined Place Names

## Goal

Add user-defined place names so the system can label coordinate-based places with meaningful personal names.

This converts:

geocoded location → user-meaningful place

Examples:

- “Audrey’s House”
- “Grandma’s House”
- “Cabin”
- “Office”
- “Disneyland Trip Area”

This is a **human-controlled place naming milestone**, not a geocoding or AI milestone.

---

## Context

System already supports:

- canonical GPS per asset (12.8)
- stable Place entities (12.9)
- Places navigation UI (12.10)
- reverse geocoding / geographic hierarchy (12.11)
- Photo Review workspace and filters

Current limitation:

- places are displayed using machine-derived labels such as city/state/address
- user cannot assign a personal or semantic name to a place
- important recurring places are not yet human-friendly

---

## Core Principle

The user-defined place alias is the preferred human-facing label for a place.

Machine-derived geocoding remains preserved, but user naming takes display priority.

---

## Scope

### In Scope

- add editable alias/name field to Place
- allow user to set, edit, and clear a place alias
- display alias in Places view when present
- use geocoded label as fallback when no alias exists
- keep alias human-controlled only

### Out of Scope

- place merging/splitting
- moving assets between places
- landmark recognition
- image-based location inference
- automatic alias suggestion
- map UI
- multi-alias support

---

## Required Behavior

### 1. Place Alias Field

Add to Place:

- `alias` or `display_name` nullable string

Recommended name:

- `user_label`

Meaning:

- user-defined name for this place
- optional
- editable
- takes display priority over geocoded label

---

### 2. Display Priority

When showing a place label, use this priority:

1. `user_label`
2. city, state
3. state, country
4. country
5. formatted_address
6. coordinates

Example:

If geocode says:

- Rancho Santa Margarita, CA

But user label is:

- Audrey’s House

UI should display:

- Audrey’s House

Geocoded information should remain available as secondary context if already shown or easy to show.

---

### 3. Editing Behavior

User must be able to:

- set alias
- edit alias
- clear alias

Clearing alias returns display to geocoded fallback.

---

### 4. UI Location

Implement alias editing in Places view.

Preferred behavior:

- selected place detail area includes editable name field
- or place list item has simple edit control

Keep UI simple.

---

### 5. Validation

Alias rules:

- trim whitespace
- empty string = clear alias
- reasonable max length, e.g. 120 characters
- no uniqueness requirement in 12.17

Reason:

- multiple places might legitimately share similar labels
- uniqueness can be revisited later

---

### 6. Non-Destructive Behavior

Setting an alias must not alter:

- coordinates
- geocoded fields
- asset membership
- place grouping

Alias is a display/user layer only.

---

## Backend Requirements

### 1. Schema Update

Add nullable string field to Place:

- `user_label`

---

### 2. API Support

Add endpoint or extend existing Places endpoint to update label.

Suggested endpoint:

POST /api/places/{place_id}/label

Request:

- `user_label: string | null`

Response:

- updated Place summary/detail

---

### 3. Service Logic

Add place label update service:

- trim value
- convert empty string to null
- persist change
- return updated display label

---

### 4. Display Label

Backend should expose:

- `user_label`
- `display_label`

Where `display_label` follows the priority order above.

---

## Frontend Requirements

### 1. Places UI

In Places view:

- show user label as primary name when present
- show geocoded label / coordinates as secondary context if simple

---

### 2. Edit Control

Add simple edit action:

- Edit Name
- Save
- Cancel
- Clear

Keep it lightweight.

---

### 3. Refresh Behavior

After save/clear:

- update selected place
- update list label
- no full page reload

---

## Validation Checklist

- user can set place alias
- user can edit place alias
- user can clear place alias
- alias displays before geocoded label
- geocoded data remains unchanged
- place membership remains unchanged
- no regressions to Places view
- no regressions to Photo Review or location filters

---

## Definition of Done

- places can have human-readable user-defined names
- aliases are editable and reversible
- user labels take display priority
- machine-derived location remains preserved
- Places becomes more personally meaningful without changing location logic

---

## Constraints

- must not alter place grouping
- must not alter geocoding data
- must not infer labels automatically
- must remain user-controlled
- must keep UI simple

---

## Notes

This milestone introduces the first human semantic layer on top of the location system.

Current layers:

- canonical GPS = objective coordinate truth
- Place = coordinate cluster
- geocode = machine-derived geographic label
- user_label = human-defined semantic place name

Future milestones may include:

- place merge/split
- multiple aliases
- landmark labels
- image-based place recognition
- place-based search

---

## Summary

This milestone lets the user rename machine-derived places into meaningful personal places while preserving all underlying geographic data.
