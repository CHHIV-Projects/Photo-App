import { describe, expect, it } from "vitest";

import type { IcloudIntakeImportStatus } from "@/types/ui-api";
import { isIcloudChunkActive } from "./IcloudRunWorkflowPanel";


function status(overrides: Partial<IcloudIntakeImportStatus>): IcloudIntakeImportStatus {
  return overrides as IcloudIntakeImportStatus;
}

describe("iCloud chunk polling state", () => {
  it("treats a starting or running chunk as active", () => {
    expect(isIcloudChunkActive(status({ import_status: "running", current_phase: "chunk_starting" }))).toBe(true);
    expect(isIcloudChunkActive(status({ import_status: "running", current_phase: "chunk_2_running" }))).toBe(true);
  });

  it("does not keep polling while safely waiting between chunks", () => {
    expect(isIcloudChunkActive(status({ import_status: "running", current_phase: "waiting_for_next_chunk" }))).toBe(false);
    expect(isIcloudChunkActive(status({ import_status: "resume_available", current_phase: "resume_available" }))).toBe(false);
    expect(isIcloudChunkActive(null)).toBe(false);
  });
});
