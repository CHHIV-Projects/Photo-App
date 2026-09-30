import { describe, expect, it } from "vitest";

import type { SourceIntakeReportSummary } from "@/types/ui-api";
import {
  readWorkbenchSelection,
  resolveCanonicalTerminalReportFilename,
  writeWorkbenchSelection,
} from "./ingestion-session-ui";


describe("ingestion workbench session state", () => {
  it("round-trips the selected provider, device, and Source", () => {
    const values = new Map<string, string>();
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
    };
    writeWorkbenchSelection(storage, { sourceType: "icloud", deviceKey: "icloud-account", sourceId: 14 });
    expect(readWorkbenchSelection(storage)).toEqual({ sourceType: "icloud", deviceKey: "icloud-account", sourceId: 14 });
  });

  it("maps an iCloud batch wrapper to the canonical Source Intake report by run ID", () => {
    const reports = [{ report_filename: "source_intake_21.json", ingestion_run_id: 21 }] as SourceIntakeReportSummary[];
    expect(resolveCanonicalTerminalReportFilename(
      "/app/storage/logs/icloud_batch_source_intake_reports/icloud_batch_source_intake_10.json",
      21,
      reports,
    )).toBe("source_intake_21.json");
  });

  it("does not send an unlisted wrapper filename to the canonical report endpoint", () => {
    expect(resolveCanonicalTerminalReportFilename(
      "icloud_batch_source_intake_10.json",
      null,
      [],
    )).toBeNull();
  });
});
