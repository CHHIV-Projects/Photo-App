import { describe, expect, it } from "vitest";

import {
  conciseSourceDeviceLabel,
  normalSelectorSourceTypes,
  sourcePresentationType,
  sourceSelectorEndpointFieldLabel,
  sourceSelectorEndpointLabel,
  sourceWorkbenchKind,
} from "./source-provider-ui";
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

  it("classifies Server only from mounted provider plus durable Local endpoint type", () => {
    expect(sourcePresentationType(profile({ provider_kind: "mounted", endpoint_source_type: "local" }))).toBe("server");
    expect(sourcePresentationType(profile({ provider_kind: "windows_helper", endpoint_source_type: "local" }))).toBe("local");
    expect(sourcePresentationType(profile({ provider_kind: "mounted", endpoint_source_type: "nas" }))).toBe("nas");
  });

  it("uses concise device aliases and hides unvalidated Windows provider types", () => {
    expect(conciseSourceDeviceLabel(profile())).toBe("Chuck_Notebook");
    expect(normalSelectorSourceTypes(["local", "nas", "external", "removable", "optical", "icloud"])).toEqual(["local", "nas", "external", "removable", "icloud"]);
  });

  it("presents a NAS endpoint as a registered share rather than a generic device", () => {
    const nasProfile = profile({
      provider_kind: "mounted",
      endpoint_source_type: "nas",
      endpoint_alias: "Camera imports",
      source_root_path: "/app/sources/nas/location/Camera imports",
    });

    expect(sourceSelectorEndpointFieldLabel("nas")).toBe("Registered NAS Share");
    expect(sourceSelectorEndpointFieldLabel("external")).toBe("Device");
    expect(sourceSelectorEndpointLabel(nasProfile, "Photo Organizer NAS — \\\\Photos")).toBe(
      "Photo Organizer NAS — \\\\Photos",
    );
  });

  it("falls back to a canonical UNC server/share instead of a legacy NAS alias", () => {
    expect(sourceSelectorEndpointLabel(profile({
      provider_kind: "mounted",
      endpoint_source_type: "nas",
      endpoint_alias: "Camera imports",
      source_root_path: "\\\\HENDERSON-NAS\\Photos\\Camera imports",
    }))).toBe("\\\\HENDERSON-NAS\\Photos");
  });
});
