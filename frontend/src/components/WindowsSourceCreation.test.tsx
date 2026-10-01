import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";
import WindowsSourceCreation from "./WindowsSourceCreation";


vi.mock("@/lib/api", () => ({
  confirmWindowsSourceUiCreation: vi.fn(),
  getWindowsSourceUiComputers: vi.fn(),
  getWindowsSourceUiOperation: vi.fn(),
  planWindowsSourceUiCreation: vi.fn(),
  resolveWindowsPortableDiscovery: vi.fn(),
  startWindowsSourceUiCreationProbe: vi.fn(),
  startWindowsPortableDiscovery: vi.fn(),
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
  vi.mocked(api.getWindowsSourceUiComputers).mockResolvedValue({ computers: [computer] });
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
    device_alias: "Chuck_Notebook",
    windows_root: exactRoot,
    profile_name: profileName,
    device_action: "reuse_existing_endpoint",
    profile_action: "reuse_existing_source",
    blockers: [],
    warnings: [],
  });
  const discovery = {
    stage: "ready" as const,
    safe_message: "Select a detected Source device.",
    observation_tokens: ["22222222-2222-2222-2222-222222222222"],
    candidates: [{
      candidate_token: "22222222-2222-2222-2222-222222222222:0",
      device_alias: "External 1",
      known_device: true,
      current_root: "H:\\",
      drive_type: "fixed",
      current_route_count: 1,
    }],
  };
  vi.mocked(api.startWindowsPortableDiscovery).mockResolvedValue(discovery);
  vi.mocked(api.resolveWindowsPortableDiscovery).mockResolvedValue(discovery);
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

    fireEvent.change(screen.getByLabelText("Folder"), {
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

  it("stops exact existing Profile reuse and explains that the entered name is unused", async () => {
    const launch = vi.fn();
    render(
      <WindowsSourceCreation
        computers={[computer]}
        sourceType="local"
        launchWindowsAccess={launch}
        onComplete={vi.fn()}
      />,
    );

    fireEvent.change(screen.getByLabelText("Folder"), {
      target: { value: exactRoot },
    });
    fireEvent.change(screen.getByLabelText("Source Profile name"), {
      target: { value: "Replacement profile name" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Review Source" }));

    expect(await screen.findByRole("heading", { name: "Source Profile already exists" })).toBeInTheDocument();
    expect(await screen.findByText("Reuse existing Profile")).toBeInTheDocument();
    expect(screen.getByText("Existing device")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(`already registered as ${profileName}`);
    expect(screen.getByRole("alert")).toHaveTextContent("entered name Replacement profile name will not be used");
    expect(screen.getByRole("alert")).toHaveTextContent("Select the existing Profile in Source Selector");
    expect(screen.queryByRole("button", { name: "Create Source" })).not.toBeInTheDocument();
    expect(launch).toHaveBeenCalledTimes(1);
    expect(api.confirmWindowsSourceUiCreation).not.toHaveBeenCalled();
  });

  it("uses the same creation path for External without conflating computer and device", async () => {
    const launch = vi.fn();
    vi.mocked(api.planWindowsSourceUiCreation).mockResolvedValue({
      plan_status: "ready",
      device_alias: "External 1",
      windows_root: "H:\\Pictures",
      profile_name: "External photos",
      device_action: "reuse_existing_endpoint",
      profile_action: "create_new_source",
      blockers: [],
      warnings: [],
    });
    render(<WindowsSourceCreation computers={[computer]} sourceType="external" launchWindowsAccess={launch} onComplete={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Detect connected External devices" }));
    fireEvent.change(await screen.findByLabelText("Detected External device"), { target: { value: "22222222-2222-2222-2222-222222222222:0" } });
    fireEvent.change(screen.getByLabelText(/Folder within device/), { target: { value: "Pictures" } });
    fireEvent.change(screen.getByLabelText("Source Profile name"), { target: { value: "External photos" } });
    fireEvent.click(screen.getByRole("button", { name: "Review Source" }));

    expect(await screen.findByText("Review Windows External Source")).toBeInTheDocument();
    expect(api.startWindowsSourceUiCreationProbe).toHaveBeenCalledWith(expect.objectContaining({
      access_node_id: null,
      discovery_candidate_token: "22222222-2222-2222-2222-222222222222:0",
      source_type: "external",
      device_alias: "External 1",
      endpoint_relative_root: "Pictures",
      windows_root: undefined,
    }));
    expect(api.getWindowsSourceUiComputers).toHaveBeenCalled();
    expect(vi.mocked(api.getWindowsSourceUiComputers).mock.invocationCallOrder[0]).toBeLessThan(
      vi.mocked(api.startWindowsPortableDiscovery).mock.invocationCallOrder[0],
    );
  });

  it("rejects a drive-qualified portable folder before submission", async () => {
    render(<WindowsSourceCreation computers={[computer]} sourceType="external" launchWindowsAccess={vi.fn()} onComplete={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Detect connected External devices" }));
    fireEvent.change(await screen.findByLabelText("Detected External device"), { target: { value: "22222222-2222-2222-2222-222222222222:0" } });
    fireEvent.change(screen.getByLabelText(/Folder within device/), { target: { value: "H:\\Pictures" } });
    fireEvent.change(screen.getByLabelText("Source Profile name"), { target: { value: "External photos" } });
    fireEvent.click(screen.getByRole("button", { name: "Review Source" }));
    expect(screen.getAllByText(/Enter a folder relative to the selected device/).length).toBeGreaterThan(0);
    expect(api.startWindowsSourceUiCreationProbe).not.toHaveBeenCalled();
  });

  it("asks for a durable Device name only after an unknown Removable device is detected", async () => {
    const discovery = {
      stage: "ready" as const,
      safe_message: "Select a detected Source device.",
      observation_tokens: ["33333333-3333-3333-3333-333333333333"],
      candidates: [{
        candidate_token: "33333333-3333-3333-3333-333333333333:0",
        device_alias: null,
        known_device: false,
        current_root: "X:\\",
        drive_type: "removable",
        current_route_count: 1,
      }],
    };
    vi.mocked(api.startWindowsPortableDiscovery).mockResolvedValue(discovery);
    vi.mocked(api.resolveWindowsPortableDiscovery).mockResolvedValue(discovery);
    vi.mocked(api.planWindowsSourceUiCreation).mockResolvedValue({
      plan_status: "ready",
      device_alias: "8GB Card",
      windows_root: "X:\\Family Photos",
      profile_name: "8GB Card Test",
      device_action: "create_new_endpoint",
      profile_action: "create_new_source",
      blockers: [],
      warnings: [],
    });

    render(<WindowsSourceCreation computers={[computer]} sourceType="removable" launchWindowsAccess={vi.fn()} onComplete={vi.fn()} />);

    expect(screen.queryByLabelText("Device name")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Computer")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Detect connected Removable devices" }));
    fireEvent.change(await screen.findByLabelText("Detected Removable device"), {
      target: { value: "33333333-3333-3333-3333-333333333333:0" },
    });

    expect(screen.getByLabelText("Device name")).toBeInTheDocument();
    expect(screen.getByText("Current access: X:\\")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Device name"), { target: { value: "8GB Card" } });
    fireEvent.change(screen.getByLabelText(/Folder within device/), { target: { value: "Family Photos" } });
    fireEvent.change(screen.getByLabelText("Source Profile name"), { target: { value: "8GB Card Test" } });
    fireEvent.click(screen.getByRole("button", { name: "Review Source" }));

    expect(await screen.findByText("Review Windows Removable Source")).toBeInTheDocument();
    expect(api.startWindowsSourceUiCreationProbe).toHaveBeenCalledWith(expect.objectContaining({
      access_node_id: null,
      discovery_candidate_token: "33333333-3333-3333-3333-333333333333:0",
      source_type: "removable",
      device_alias: "8GB Card",
      endpoint_relative_root: "Family Photos",
      windows_root: undefined,
      profile_name: "8GB Card Test",
    }));
  });

  it("asks for a durable Device name after a verified unknown External device is detected", async () => {
    const discovery = {
      stage: "ready" as const,
      safe_message: "Select a detected Source device.",
      observation_tokens: ["44444444-4444-4444-4444-444444444444"],
      candidates: [{
        candidate_token: "44444444-4444-4444-4444-444444444444:0",
        device_alias: null,
        known_device: false,
        current_root: "H:\\",
        drive_type: "fixed",
        current_route_count: 1,
      }],
    };
    vi.mocked(api.startWindowsPortableDiscovery).mockResolvedValue(discovery);
    vi.mocked(api.resolveWindowsPortableDiscovery).mockResolvedValue(discovery);

    render(<WindowsSourceCreation computers={[computer]} sourceType="external" launchWindowsAccess={vi.fn()} onComplete={vi.fn()} />);

    expect(screen.queryByLabelText("Device name")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Detect connected External devices" }));
    fireEvent.change(await screen.findByLabelText("Detected External device"), {
      target: { value: "44444444-4444-4444-4444-444444444444:0" },
    });

    expect(screen.getByLabelText("Device name")).toBeInTheDocument();
    expect(screen.getByText("Current access: H:\\")).toBeInTheDocument();
  });
});
