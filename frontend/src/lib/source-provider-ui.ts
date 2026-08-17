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

export function normalSelectorSourceTypes(values: string[]): string[] {
  const unvalidated = new Set(["external", "removable", "optical"]);
  return values.filter((value) => !unvalidated.has(value));
}
