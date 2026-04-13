**Milestone 11.10 — Collections and Albums Foundation**

**Goal**

Introduce a user-defined grouping layer that allows the archive owner to create and manage **manual collections/albums** built from curated photo selections.

This milestone adds a foundational organizational layer above raw browsing so the user can preserve meaningful sets of photos independent of automatic event, place, person, or timeline grouping.

**Context**

The current system already supports:

-   ingestion and deduplication
-   provenance and duplicate lineage
-   capture-type classification and date trust
-   event grouping
-   face detection, clustering, and person assignment
-   photos, events, places, people, review, unassigned faces, and timeline browsing

Current limitation:

-   all groupings are system-derived
-   there is no durable user-created grouping layer for:
    -   curated sets
    -   family albums
    -   trip selections
    -   thematic groupings
    -   project/review sets

This milestone introduces the first manual curation layer.

**Scope**

**In Scope**

-   data model for manual collections/albums
-   create/read/update/delete collections
-   add/remove assets from collections
-   list collections
-   view collection contents
-   basic collection metadata
-   minimal UI for collection management
-   integration with existing photo browsing where practical

**Out of Scope**

-   sharing/external access (11.14)
-   smart/automatic collections
-   nested collections
-   collection cover image customization beyond simple default
-   advanced sorting/ranking logic
-   collaboration/multi-user editing
-   bulk rule-based collections
-   slideshow/export workflows

**Product Intent**

The user should be able to do things like:

-   create an album called “Hawaii Trip 2019”
-   save selected photos into it
-   create a collection for “Best Family Photos”
-   curate a manual set across many events, years, and places
-   browse those sets later as durable user-defined groupings

Collections/albums should be:

-   manual
-   durable
-   simple
-   independent of automatic clustering logic

**Terminology**

For this milestone, choose **one user-facing term** and use it consistently.

Recommended:

-   **Albums**

Internal model name may remain Collection if preferred, but UI should use one term consistently.

Unless there is a strong reason otherwise:

-   backend/model may use Collection
-   frontend/user-facing label should use **Album**

**Functional Requirements**

**1. Collection/Album Data Model**

Add a manual grouping entity with at minimum:

-   id
-   name
-   description (optional)
-   created_at
-   updated_at

Add membership relationship:

-   collection ↔ assets (many-to-many)

Optional but recommended:

-   cover_asset_sha256 or equivalent nullable reference
-   use first asset as default cover if explicit cover not set

**2. CRUD Support**

Support:

-   create collection
-   rename collection
-   update description
-   delete collection
-   view collection details
-   list all collections

Requirements:

-   deletion removes membership links only, not assets
-   no destructive impact on photos or metadata
-   collection names do not need to be globally unique unless implementation strongly prefers it

**3. Membership Management**

Support:

-   add asset(s) to collection
-   remove asset(s) from collection
-   prevent duplicate membership rows
-   list assets in a collection

Requirements:

-   adding an asset to a collection must not modify the asset itself
-   the same asset may belong to multiple collections
-   exact duplicate canonical logic remains unchanged; membership attaches to the asset record selected by user

For this milestone, collection membership should use the existing asset identity directly.

**4. Browsing Collections**

User must be able to:

-   see list of collections
-   see asset count per collection
-   open a collection
-   browse photos inside that collection

At minimum:

-   collection list view
-   collection detail view with photo grid/list

**5. Integration with Existing Photo Browsing**

Add a basic way to save photos into collections from existing browsing surfaces.

Recommended minimum:

-   from Photos view or photo detail, allow:
    -   add to collection
    -   remove from collection if currently in one
-   from collection detail, allow remove from collection

Keep first version simple.  
Do not add complex multi-select batch workflows unless already easy.

**6. Cover Image Behavior**

Simple default behavior is sufficient.

Recommended:

-   use explicit cover_asset_sha256 if set
-   otherwise use earliest-added or first-added asset as collection cover

Do not overdesign cover management in this milestone.

**7. Sorting / Ordering**

Keep ordering simple.

Recommended defaults:

-   collections list: most recently updated first
-   assets within collection: date added to collection ascending or descending, coder may choose one consistent rule

If explicit per-collection custom ordering is complex, defer it.

**8. API Design**

Provide backend support for:

**Collections list**

-   list all collections with:
    -   id
    -   name
    -   description
    -   asset count
    -   cover asset if available

**Collection detail**

-   collection metadata
-   collection contents

**CRUD actions**

-   create
-   update
-   delete

**Membership actions**

-   add assets
-   remove assets

Keep API explicit and simple.  
Do not create a generalized tagging framework.

**9. Frontend Requirements**

Add a dedicated top-level browsing surface for collections/albums.

Recommended:

-   top-level **Albums** view
-   list of albums
-   create album action
-   album detail page/panel with photo grid
-   simple add/remove interactions

Use current UI patterns where practical.

No advanced modal/workflow complexity required.

**10. Non-Destructive Guarantee**

Collections are a curation layer only.

They must not:

-   move assets
-   modify provenance
-   alter duplicate lineage
-   alter event assignments
-   alter people/faces metadata

Collections only store references to assets.

**Backend Requirements**

**Models**

Add collection + membership model(s)

**Services**

Add collection CRUD + membership services

**API**

Add collection endpoints and response schemas

**DB**

Use safe migrations / initialization consistent with current project patterns

**Frontend Requirements**

**Albums View**

Provide:

-   album list
-   create album action
-   album detail with contents

**Photo Integration**

Provide a simple path to add photo to album from existing photo browsing UI

**Stability**

Do not break existing Photos / Timeline / Events / People / Review flows

**Validation Checklist**

**Data / API**

-   collection can be created
-   collection can be renamed and described
-   collection can be deleted without affecting assets
-   asset can be added to collection
-   asset can be removed from collection
-   duplicate membership is prevented
-   collection detail returns correct contents and counts

**UI**

-   user can create an album
-   user can open album list
-   user can open an album and view its photos
-   user can add a photo to an album
-   user can remove a photo from an album

**Regression**

-   no change to asset metadata/provenance
-   no change to event grouping
-   no change to face/identity workflows
-   existing views remain stable

**Usability**

-   albums feel simple and understandable
-   manual grouping is durable across reruns

**Deliverables**

-   collection/album data model
-   membership model
-   backend CRUD + membership services
-   API endpoints/schemas
-   frontend Albums view
-   basic photo-to-album interaction
-   code summary describing:
    -   data model
    -   membership behavior
    -   cover behavior
    -   ordering behavior
-   validation results from coder

**Definition of Done**

-   user can create and manage manual albums
-   user can add and remove photos from albums
-   user can browse album contents
-   albums persist independently of automatic system groupings
-   implementation is non-destructive and stable
