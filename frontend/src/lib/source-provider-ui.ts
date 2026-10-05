import type { SourceProfileSummary } from "@/types/ui-api";

export type SourceWorkbenchKind = "windows_helper" | "icloud" | "mounted";

export function sourceWorkbenchKind(profile: SourceProfileSummary): SourceWorkbenchKind {
  if (profile.provider_kind === "windows_helper") return "windows_helper";
  if (profile.provider_kind === "icloud" || profile.provider_kind === "cloud") return "icloud";
  return "mounted";
}

export function conciseSourceDeviceLabel(profile: SourceProfileSummary): string {
  return profile.endpoint_alias?.trim() || profile.source_label;
}

export function sourceSelectorEndpointFieldLabel(sourceType: string): string {
  return sourceType === "nas" ? "Registered NAS Share" : "Device";
}

export function sourceSelectorEndpointLabel(
  profile: SourceProfileSummary,
  registeredNasShareLabel?: string | null,
): string {
  if (sourcePresentationType(profile) === "nas") {
    const registeredLabel = registeredNasShareLabel?.trim();
    if (registeredLabel) return registeredLabel;

    const normalized = (profile.source_root_path ?? "").trim().replace(/\//g, "\\");
    if (normalized.startsWith("\\\\")) {
      const [server, share] = normalized.split("\\").filter(Boolean);
      if (server && share) return `\\\\${server}\\${share}`;
    }
    return profile.endpoint_alias?.trim() || `NAS share #${profile.endpoint_id ?? "unknown"}`;
  }
  if (profile.provider_kind === "icloud" || profile.provider_kind === "cloud") {
    return profile.account_username_masked ? `iCloud ${profile.account_username_masked}` : "iCloud account";
  }
  if (profile.endpoint_id == null) return "Legacy source";
  return profile.endpoint_alias?.trim() || `${sourcePresentationType(profile)} endpoint #${profile.endpoint_id}`;
}

export function sourcePresentationType(profile: SourceProfileSummary): string {
  if (profile.provider_kind === "icloud" || profile.cloud_provider === "icloud") return "icloud";
  if (profile.endpoint_source_type === "nas") return "nas";
  if (profile.endpoint_source_type === "removable_media") return "removable";
  if (profile.endpoint_source_type === "optical_media" || profile.source_type === "optical_media") return "optical";
  if (profile.provider_kind === "mounted" && profile.endpoint_source_type === "local") return "server";
  if (profile.provider_kind === "windows_helper" && profile.endpoint_source_type === "local") return "local";
  if (profile.endpoint_source_type === "external_device" || profile.source_type === "external_drive") return "external";
  return "advanced";
}

export function normalSelectorSourceTypes(values: string[]): string[] {
  const unvalidated = new Set(["optical"]);
  return values.filter((value) => !unvalidated.has(value));
}
