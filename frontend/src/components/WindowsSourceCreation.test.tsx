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
        deviceAliases={["Chuck_Notebook"]}
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
        deviceAliases={["Chuck_Notebook"]}
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
    fireEvent.click(screen.getByRole("button", { name: "Review Source" }));

    expect(await screen.findByText("Reuse existing Profile")).toBeInTheDocument();
    expect(screen.getByText("Existing device")).toBeInTheDocument();
    expect(launch).toHaveBeenCalledTimes(1);
    expect(api.confirmWindowsSourceUiCreation).not.toHaveBeenCalled();
  });
});

