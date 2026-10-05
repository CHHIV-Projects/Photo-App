# Bug Fix 007 — NAS Source Selector Share Labeling

## Defect

The Source Selector used the generic label `Device` for its first dropdown for every provider. For NAS Sources, that dropdown is keyed by durable Source Endpoint identity, and the NAS Endpoint boundary is the registered SMB share rather than the NAS appliance as a whole.

The selector also preferred `endpoint_alias` for the displayed option. A legacy NAS Endpoint alias such as `Camera imports` therefore appeared as the Device even though the Endpoint represented the registered `Photos` SMB share. The adjacent Source dropdown could also contain `Camera imports`, making the two levels appear redundant and obscuring the actual share-plus-folder relationship.

## Correct Model

For NAS:

```text
NAS appliance/server
  -> registered SMB share (Source Endpoint)
    -> relative folder + friendly name/settings (Source Profile)
```

Example:

```text
NAS appliance: HENDERSON-NAS / Photo Organizer NAS
Registered SMB share Endpoint: \\HENDERSON-NAS\Photos
Endpoint-relative Source root: Camera imports
Source Profile name: Camera imports
```

The Source Profile remains the registered share Endpoint plus one endpoint-relative root, friendly Source name, status, and Source-specific settings.

## Correction

- When NAS is selected, the first Source Selector field is labeled `Registered NAS Share` instead of `Device`.
- Registered NAS metadata is mapped to its existing `source_endpoint_id` and used to display the established share label, for example `Photo Organizer NAS — \\Photos`.
- If registration metadata is temporarily unavailable, a UNC Source path is reduced to its canonical `\\server\share` boundary before considering a legacy Endpoint alias.
- The second dropdown remains `Source` and continues to select the Source Profile beneath that share.
- The NAS summary card uses the same `Registered NAS Share` terminology.
- The NAS grouping card describes the selected item as a registered SMB share Source Endpoint instead of repeating a Source-specific filesystem path as Device metadata.
- Other provider types retain the existing `Device` terminology and grouping behavior.

## Scope and Safety

This is a presentation-only correction. It does not rename or mutate NAS registrations, Source Endpoints, Endpoint aliases, Source Profiles, relative roots, provenance, or database identity. Grouping remains keyed by the existing durable `endpoint_id`.

## Validation

Focused frontend tests cover:

- NAS-specific `Registered NAS Share` terminology;
- unchanged `Device` terminology for non-NAS providers;
- registered-share labels taking precedence over misleading legacy aliases;
- canonical UNC `\\server\share` fallback behavior.

Validation results:

- all `27` frontend tests passed across `7` test files;
- TypeScript `--noEmit` validation passed;
- the Development frontend image built successfully;
- only the Development frontend container was recreated;
- the replacement frontend reached Docker `healthy` state and returned HTTP success;
- the backend and all Source/NAS identities were left unchanged.

## Files Changed

- `frontend/src/lib/source-provider-ui.ts`
- `frontend/src/lib/source-provider-ui.test.ts`
- `frontend/src/components/IngestionView.tsx`
- `docs/bug_fixes/bug_fix_007_nas_source_selector_share_labeling.md`
