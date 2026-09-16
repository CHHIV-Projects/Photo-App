import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";
import WindowsSourceCreation from "./WindowsSourceCreation";


vi.mock("@/lib/api", () => ({
  confirmWindowsSourceUiCreation: vi.fn(),
  getWindowsSourceUiOperation: vi.fn(),
  planWindowsSourceUiCreation: vi.fn(),
  startWindowsSourceUiCreationProbe: vi.fn(),
}));

const exactRoot = "C:\\Users\\chhen\\OneDrive\\Desktop\\Exif provanace";
const profileName = "Local test 1 Exif provanace";
const computer = {
  access_node_id: "11111111-1111-1111-1111-111111111111",
  computer_alias: "Chuck_Notebook",
  paired: true,
  online: true,
  helper_version: "0.5.1",
  source_device_aliases: ["Chuck_Notebook", "External 1"],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.startWindowsSourceUiCreationProbe).mockResolvedValue({
    operation_token: "probe",
    stage: "checking_source",
    source_ready: false,
    safe_message: "Checking",
  });
  vi.mocked(api.getWindowsSourceUiOperation).mockResolvedValue({
    operation_token: "probe",
    stage: "ready",
    source_ready: true,
    safe_message: "Ready",
  });
  vi.mocked(api.planWindowsSourceUiCreation).mockResolvedValue({
    plan_status: "source_exists",
    access_node_id: computer.access_node_id,
    source_type: "local",
    device_alias: "Chuck_Notebook",
    windows_root: exactRoot,
    profile_name: profileName,
    device_action: "reuse_existing_endpoint",
    profile_action: "reuse_existing_source",
    blockers: [],
    warnings: [],
  });
});

afterEach(cleanup);

describe("Windows Source creation", () => {
  it("rejects a relative path before launching Windows access", () => {
    const launch = vi.fn();
    render(
      <WindowsSourceCreation
        computers={[computer]}
        sourceType="local"
        launchWindowsAccess={launch}
        onComplete={vi.fn()}
      />,
    );

    fireEvent.change(screen.getByLabelText("Exact Windows Local folder"), {
      target: { value: "relative\\folder" },
    });
    fireEvent.change(screen.getByLabelText("Source Profile name"), {
      target: { value: profileName },
    });
    fireEvent.click(screen.getByRole("button", { name: "Review Source" }));

    expect(screen.getAllByText("Enter an absolute Windows folder path.").length).toBeGreaterThan(0);
    expect(launch).not.toHaveBeenCalled();
    expect(api.startWindowsSourceUiCreationProbe).not.toHaveBeenCalled();
  });

  it("visibly proposes exact existing Profile reuse without confirming it", async () => {
    const launch = vi.fn();
    render(
      <WindowsSourceCreation
        computers={[computer]}
        sourceType="local"
        launchWindowsAccess={launch}
        onComplete={vi.fn()}
      />,
    );

    fireEvent.change(screen.getByLabelText("Exact Windows Local folder"), {
      target: { value: exactRoot },
    });
    fireEvent.change(screen.getByLabelText("Source Profile name"), {
      target: { value: profileName },
    });
    fireEvent.change(screen.getByLabelText("Source device name"), {
      target: { value: "Chuck_Notebook" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Review Source" }));

    expect(await screen.findByText("Reuse existing Profile")).toBeInTheDocument();
    expect(screen.getByText("Existing device")).toBeInTheDocument();
    expect(launch).toHaveBeenCalledTimes(1);
    expect(api.confirmWindowsSourceUiCreation).not.toHaveBeenCalled();
  });

  it("uses the same creation path for External without conflating computer and device", async () => {
    const launch = vi.fn();
    vi.mocked(api.planWindowsSourceUiCreation).mockResolvedValue({
      plan_status: "ready",
      access_node_id: computer.access_node_id,
      source_type: "external",
      device_alias: "External 1",
      windows_root: "H:\\Pictures",
      profile_name: "External photos",
      device_action: "reuse_existing_endpoint",
      profile_action: "create_new_source",
      blockers: [],
      warnings: [],
    });
    render(<WindowsSourceCreation computers={[computer]} sourceType="external" launchWindowsAccess={launch} onComplete={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Source device name"), { target: { value: "External 1" } });
    fireEvent.change(screen.getByLabelText("Exact Windows External folder"), { target: { value: "H:\\Pictures" } });
    fireEvent.change(screen.getByLabelText("Source Profile name"), { target: { value: "External photos" } });
    fireEvent.click(screen.getByRole("button", { name: "Review Source" }));

    expect(await screen.findByText("Review Windows External Source")).toBeInTheDocument();
    expect(api.startWindowsSourceUiCreationProbe).toHaveBeenCalledWith(expect.objectContaining({
      access_node_id: computer.access_node_id,
      source_type: "external",
      device_alias: "External 1",
    }));
  });
});
