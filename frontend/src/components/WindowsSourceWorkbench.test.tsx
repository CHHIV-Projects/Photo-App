import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import WindowsSourceWorkbench from "./WindowsSourceWorkbench";
import type { SourceProfileSummary } from "@/types/ui-api";
import * as api from "@/lib/api";


vi.mock("@/lib/api", () => ({
  advanceWindowsSourceUiRun: vi.fn(),
  confirmWindowsSourceUiRun: vi.fn(),
  getWindowsSourceUiOperation: vi.fn(),
  getWindowsSourceUiProfile: vi.fn(),
  prepareWindowsSourceUiInventory: vi.fn(),
  reviewWindowsSourceUiCandidates: vi.fn(),
  startWindowsSourceUiProbe: vi.fn(),
}));

const profile: SourceProfileSummary = {
  source_id: 4,
  source_label: "Local test 1 Exif provanace",
  source_type: "local_folder",
  provider_kind: "windows_helper",
  source_root_path: "C:\\Users\\chhen\\OneDrive\\Desktop\\Exif provanace",
  endpoint_relative_root: "Exif provanace",
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
  provenance_count: 5,
  ingestion_runs_count: 1,
  source_intake_runs_count: 1,
  icloud_acquisition_runs_count: 0,
};

const readyAccess = {
  provider_kind: "windows_helper" as const,
  source_profile_id: 4,
  profile_name: profile.source_label,
  device_alias: "Chuck_Notebook",
  windows_root: profile.source_root_path!,
  windows_access: "ready" as const,
  paired: true,
  online: true,
  helper_version: "0.5.0",
  source_readiness: "not_ready" as const,
};

const instantWait = async () => undefined;

beforeEach(() => {
  vi.mocked(api.getWindowsSourceUiProfile).mockResolvedValue(readyAccess);
  vi.mocked(api.startWindowsSourceUiProbe).mockResolvedValue({ operation_token: "probe", stage: "checking_source", source_ready: false, safe_message: "Checking" });
  vi.mocked(api.getWindowsSourceUiOperation).mockResolvedValue({ operation_token: "operation", stage: "ready", source_ready: true, safe_message: "Ready" });
  vi.mocked(api.prepareWindowsSourceUiInventory).mockResolvedValue({ operation_token: "inventory", stage: "preparing_files", source_ready: false, safe_message: "Preparing" });
  vi.mocked(api.reviewWindowsSourceUiCandidates).mockResolvedValue({ workflow_token: "run", stage: "awaiting_confirmation", files_to_process: 5, total_bytes: 4_970_248, profile_name: profile.source_label, windows_root: profile.source_root_path!, safe_message: "Review" });
});

describe("Windows Source workbench", () => {
  it("shows ready state, candidate confirmation, progress, and unchanged-repeat result", async () => {
    vi.mocked(api.confirmWindowsSourceUiRun).mockResolvedValue({ workflow_token: "run", stage: "complete", files_total: 5, files_completed: 5, expected_bytes: 4_970_248, transferred_bytes: 4_970_248, new_library_items: 0, already_represented: 5, failed_items: 0, safe_message: "Run complete." });
    render(<WindowsSourceWorkbench profile={profile} wait={instantWait} />);
    expect((await screen.findAllByText("Ready")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Run Ingestion" }));
    expect(await screen.findByRole("button", { name: "Start Ingestion" })).toBeInTheDocument();
    expect(screen.getByText(/Files to process:/).parentElement).toHaveTextContent("5");
    fireEvent.click(screen.getByRole("button", { name: "Start Ingestion" }));
    expect(await screen.findByText("Run complete.")).toBeInTheDocument();
    expect(screen.getByText(/New library items:/).parentElement).toHaveTextContent("0");
    expect(screen.getByText(/Already represented:/).parentElement).toHaveTextContent("5");
    expect(screen.queryByText(/credential|token|sha256|opaque/i)).not.toBeInTheDocument();
  });

  it("invokes the exact URI launch synchronously while offline, then continues after heartbeat", async () => {
    const launch = vi.fn();
    vi.mocked(api.getWindowsSourceUiProfile)
      .mockResolvedValueOnce({ ...readyAccess, online: false, windows_access: "not_available" })
      .mockResolvedValue(readyAccess);
    render(<WindowsSourceWorkbench profile={profile} launchWindowsAccess={launch} wait={instantWait} />);
    await screen.findByText("Not available");
    fireEvent.click(screen.getByRole("button", { name: "Run Ingestion" }));
    expect(launch).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole("button", { name: "Start Ingestion" })).toBeInTheDocument();
  });

  it("stops bounded polling with a user-safe launch failure", async () => {
    vi.mocked(api.getWindowsSourceUiProfile).mockResolvedValue({ ...readyAccess, online: false, windows_access: "not_available" });
    render(<WindowsSourceWorkbench profile={profile} launchWindowsAccess={vi.fn()} launchTimeoutMs={0} wait={instantWait} />);
    await screen.findByText("Not available");
    fireEvent.click(screen.getByRole("button", { name: "Run Ingestion" }));
    expect(await screen.findByText("Windows access could not be started.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try Again" })).toBeInTheDocument();
  });
});
