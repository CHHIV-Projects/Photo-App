import { describe, expect, it } from "vitest";

import { conciseSourceDeviceLabel, normalSelectorSourceTypes, sourceWorkbenchKind } from "./source-provider-ui";
import type { SourceProfileSummary } from "@/types/ui-api";


function profile(overrides: Partial<SourceProfileSummary> = {}): SourceProfileSummary {
  return {
    source_id: 3,
    source_label: "Windows photos",
    source_type: "local_folder",
    provider_kind: "windows_helper",
    source_root_path: "/looks/linux/but-is-not-used-for-routing",
    endpoint_relative_root: null,
    endpoint_id: 2,
    endpoint_alias: "Chuck_Notebook",
    endpoint_source_type: "local",
    profile_status: "active",
    cloud_provider: null,
    acquisition_method: null,
    managed_staging_path: null,
    account_username_masked: null,
    account_username: null,
    first_seen_at: null,
    last_run_at: null,
    provenance_count: 0,
    ingestion_runs_count: 0,
    source_intake_runs_count: 0,
    icloud_acquisition_runs_count: 0,
    ...overrides,
  };
}

describe("provider-derived Source routing", () => {
  it("routes Windows Local by provider kind and not path, alias, name, or source type", () => {
    expect(sourceWorkbenchKind(profile())).toBe("windows_helper");
    expect(sourceWorkbenchKind(profile({ provider_kind: "mounted", source_root_path: "C:\\Photos", endpoint_alias: "Windows-like" }))).toBe("mounted");
  });

  it("preserves mounted and iCloud routing", () => {
    expect(sourceWorkbenchKind(profile({ provider_kind: "mounted" }))).toBe("mounted");
    expect(sourceWorkbenchKind(profile({ provider_kind: "icloud", source_type: "cloud_export", cloud_provider: "icloud" }))).toBe("icloud");
  });

  it("uses concise device aliases and hides unvalidated Windows provider types", () => {
    expect(conciseSourceDeviceLabel(profile())).toBe("Chuck_Notebook");
    expect(normalSelectorSourceTypes(["local", "nas", "external", "removable", "optical", "icloud"])).toEqual(["local", "nas", "icloud"]);
  });
});
