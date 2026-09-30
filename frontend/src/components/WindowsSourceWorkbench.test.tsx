import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import WindowsSourceWorkbench from "./WindowsSourceWorkbench";
import type { SourceProfileSummary } from "@/types/ui-api";
import * as api from "@/lib/api";


vi.mock("@/lib/api", () => ({
  advanceWindowsSourceUiRun: vi.fn(),
  confirmWindowsSourceUiRun: vi.fn(),
  getLatestWindowsSourceUiRun: vi.fn(),
  getWindowsSourceUiRun: vi.fn(),
  getWindowsSourceUiOperation: vi.fn(),
  getWindowsSourceUiProfile: vi.fn(),
  prepareWindowsSourceUiInventory: vi.fn(),
  reviewWindowsSourceUiCandidates: vi.fn(),
  resolveWindowsSourceUiRoute: vi.fn(),
  startWindowsSourceUiRouteCheck: vi.fn(),
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
  vi.clearAllMocks();
  vi.mocked(api.getWindowsSourceUiProfile).mockResolvedValue(readyAccess);
  vi.mocked(api.getLatestWindowsSourceUiRun).mockResolvedValue(null);
  vi.mocked(api.startWindowsSourceUiProbe).mockResolvedValue({ operation_token: "probe", stage: "checking_source", source_ready: false, safe_message: "Checking" });
  vi.mocked(api.getWindowsSourceUiOperation).mockResolvedValue({ operation_token: "operation", stage: "ready", source_ready: true, safe_message: "Ready" });
  vi.mocked(api.prepareWindowsSourceUiInventory).mockResolvedValue({ operation_token: "inventory", stage: "preparing_files", source_ready: false, safe_message: "Preparing" });
  vi.mocked(api.reviewWindowsSourceUiCandidates).mockResolvedValue({ workflow_token: "run", stage: "awaiting_confirmation", files_to_process: 5, inventory_candidates: 6, predictable_rejections: 1, expected_chunks: 1, total_bytes: 4_970_248, profile_name: profile.source_label, windows_root: profile.source_root_path!, safe_message: "Review" });
});

afterEach(() => cleanup());

describe("Windows Source workbench", () => {
  it("shows ready state, candidate confirmation, progress, and unchanged-repeat result", async () => {
    const completed = { workflow_token: "run", stage: "complete" as const, source_profile_id: profile.source_id, source_label: profile.source_label, started_at: "2026-09-30T00:00:00Z", finished_at: "2026-09-30T00:01:00Z", files_total: 5, files_completed: 5, inventory_candidates: 6, predictable_rejections: 1, chunks_completed: 1, chunks_total: 1, files_remaining: 0, expected_bytes: 4_970_248, transferred_bytes: 4_970_248, new_library_items: 0, already_represented: 5, failed_items: 0, safe_message: "Run complete." };
    const onComplete = vi.fn();
    vi.mocked(api.confirmWindowsSourceUiRun).mockResolvedValue(completed);
    render(<WindowsSourceWorkbench profile={profile} wait={instantWait} onComplete={onComplete} />);
    expect((await screen.findAllByText("Ready")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Run Ingestion" }));
    expect(await screen.findByRole("button", { name: "Start Ingestion" })).toBeInTheDocument();
    expect(api.prepareWindowsSourceUiInventory).toHaveBeenCalledWith(profile.source_id, "operation");
    expect(screen.getByText(/Files to process:/).parentElement).toHaveTextContent("5");
    fireEvent.click(screen.getByRole("button", { name: "Start Ingestion" }));
    expect(await screen.findByText("Run complete.")).toBeInTheDocument();
    expect(screen.getByText(/New library items:/).parentElement).toHaveTextContent("0");
    expect(screen.getByText(/Already represented:/).parentElement).toHaveTextContent("5");
    expect(onComplete).toHaveBeenCalledWith(completed);
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

  it("shows a computer choice only for verified portable route ambiguity", async () => {
    const portable = {
      ...profile,
      source_id: 5,
      source_label: "External photos",
      source_type: "external_drive" as const,
      endpoint_source_type: "external_device" as const,
      endpoint_alias: "Family Archive Drive",
      source_root_path: "H:\\Pictures",
    };
    vi.mocked(api.startWindowsSourceUiRouteCheck).mockResolvedValue({
      stage: "checking_routes",
      safe_message: "Checking",
      observation_tokens: ["one", "two"],
      probe_operation_token: null,
      routes: [],
    });
    vi.mocked(api.resolveWindowsSourceUiRoute)
      .mockResolvedValueOnce({
        stage: "ambiguous",
        safe_message: "Choose a route",
        observation_tokens: ["one", "two"],
        probe_operation_token: null,
        routes: [
          { access_node_id: "node-one", computer_alias: "Chuck Desktop" },
          { access_node_id: "node-two", computer_alias: "Family Laptop" },
        ],
      })
      .mockResolvedValueOnce({
        stage: "checking_source",
        safe_message: "Verifying",
        observation_tokens: ["one", "two"],
        probe_operation_token: "selected-probe",
        routes: [],
      });
    const view = render(<WindowsSourceWorkbench profile={portable} wait={instantWait} />);
    expect((await view.findAllByText("Ready")).length).toBeGreaterThan(0);
    fireEvent.click(view.getByRole("button", { name: "Run Ingestion" }));
    expect(await view.findByRole("button", { name: "Chuck Desktop" })).toBeInTheDocument();
    expect(view.getByRole("button", { name: "Family Laptop" })).toBeInTheDocument();
    expect(api.prepareWindowsSourceUiInventory).not.toHaveBeenCalled();
    fireEvent.click(view.getByRole("button", { name: "Family Laptop" }));
    expect(await view.findByRole("button", { name: "Start Ingestion" })).toBeInTheDocument();
    expect(api.resolveWindowsSourceUiRoute).toHaveBeenLastCalledWith(portable.source_id, ["one", "two"], "node-two");
  });

  it("restores and polls a durable parent after returning to the Source", async () => {
    const running = {
      workflow_token: "durable-parent",
      stage: "transferring_files" as const,
      files_total: 267,
      files_completed: 100,
      inventory_candidates: 270,
      predictable_rejections: 3,
      chunks_completed: 1,
      chunks_total: 3,
      files_remaining: 167,
      expected_bytes: 10_000,
      transferred_bytes: 4_000,
      new_library_items: 90,
      already_represented: 10,
      failed_items: 0,
      safe_message: "Transferred chunk 1 of 3.",
    };
    vi.mocked(api.getLatestWindowsSourceUiRun).mockResolvedValue(running);
    vi.mocked(api.getWindowsSourceUiRun).mockResolvedValue({
      ...running,
      stage: "complete",
      files_completed: 267,
      chunks_completed: 3,
      files_remaining: 0,
      transferred_bytes: 10_000,
      new_library_items: 257,
      safe_message: "Run complete.",
    });
    const onComplete = vi.fn();
    render(<WindowsSourceWorkbench profile={profile} wait={instantWait} onComplete={onComplete} />);
    expect(await screen.findByText("Run complete.")).toBeInTheDocument();
    expect(screen.getByText(/Chunks:/).parentElement).toHaveTextContent("3 / 3");
    expect(api.getWindowsSourceUiRun).toHaveBeenCalledWith("durable-parent");
    expect(onComplete).toHaveBeenCalledWith(expect.objectContaining({ workflow_token: "durable-parent", stage: "complete" }));
  });
});
