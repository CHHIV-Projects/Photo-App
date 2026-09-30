import type { SourceIntakeReportSummary } from "@/types/ui-api";


const WORKBENCH_SELECTION_KEY = "photo-organizer.ingestion.workbench-selection.v1";
export type PersistedOperatorSourceType = "local" | "external" | "removable" | "server" | "nas" | "icloud" | "optical" | "advanced";

const SOURCE_TYPES = new Set<PersistedOperatorSourceType>([
  "local",
  "external",
  "removable",
  "server",
  "nas",
  "icloud",
  "optical",
  "advanced",
]);

export interface PersistedWorkbenchSelection {
  sourceType: PersistedOperatorSourceType;
  deviceKey: string | null;
  sourceId: number | null;
}

type ReadStorage = Pick<Storage, "getItem">;
type WriteStorage = Pick<Storage, "setItem">;

export function readWorkbenchSelection(storage: ReadStorage | null): PersistedWorkbenchSelection | null {
  if (!storage) {
    return null;
  }
  try {
    const parsed = JSON.parse(storage.getItem(WORKBENCH_SELECTION_KEY) ?? "null") as Partial<PersistedWorkbenchSelection> | null;
    if (!parsed || !SOURCE_TYPES.has(parsed.sourceType as PersistedOperatorSourceType)) {
      return null;
    }
    return {
      sourceType: parsed.sourceType as PersistedOperatorSourceType,
      deviceKey: typeof parsed.deviceKey === "string" && parsed.deviceKey ? parsed.deviceKey : null,
      sourceId: typeof parsed.sourceId === "number" && Number.isInteger(parsed.sourceId) ? parsed.sourceId : null,
    };
  } catch {
    return null;
  }
}

export function writeWorkbenchSelection(
  storage: WriteStorage | null,
  selection: PersistedWorkbenchSelection,
): void {
  if (!storage) {
    return;
  }
  storage.setItem(WORKBENCH_SELECTION_KEY, JSON.stringify(selection));
}

function extractFilename(path: string | null): string | null {
  if (!path) {
    return null;
  }
  const pieces = path.split(/[\\/]/).filter(Boolean);
  return pieces.at(-1) ?? null;
}

export function resolveCanonicalTerminalReportFilename(
  statusReportPath: string | null,
  statusIngestionRunId: number | null,
  reports: SourceIntakeReportSummary[],
): string | null {
  if (statusIngestionRunId != null) {
    const byRun = reports.find((report) => report.ingestion_run_id === statusIngestionRunId);
    if (byRun) {
      return byRun.report_filename;
    }
  }
  const extracted = extractFilename(statusReportPath);
  return extracted && reports.some((report) => report.report_filename === extracted) ? extracted : null;
}
