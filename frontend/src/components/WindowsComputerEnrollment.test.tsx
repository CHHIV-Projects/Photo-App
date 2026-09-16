import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";
import WindowsComputerEnrollment from "./WindowsComputerEnrollment";


vi.mock("@/lib/api", () => ({
  createWindowsHelperPairing: vi.fn(),
  getWindowsHelperStatuses: vi.fn(),
}));

const authorization = {
  access_node_id: "11111111-1111-1111-1111-111111111111",
  access_node_label: "Family laptop",
  pairing_id: "p_safe",
  pairing_code: "p_safe.one-time-secret-value-that-is-long-enough",
  expires_at: "2026-09-15T12:10:00Z",
  status: "pending" as const,
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.createWindowsHelperPairing).mockResolvedValue(authorization);
  vi.mocked(api.getWindowsHelperStatuses).mockResolvedValue({
    helpers: [{
      access_node_id: authorization.access_node_id,
      access_node_label: authorization.access_node_label,
      access_node_status: "active",
      credential_status: "active",
      last_seen_at: "2026-09-15T12:01:00Z",
    }],
  });
});

afterEach(cleanup);

describe("Windows computer enrollment", () => {
  it("uses the existing pair command without embedding the one-time code", async () => {
    render(<WindowsComputerEnrollment onPaired={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Add / Pair Windows Device" }));
    fireEvent.change(screen.getByLabelText("Computer-friendly name"), { target: { value: "Family laptop" } });
    fireEvent.click(screen.getByRole("button", { name: "Begin Pairing" }));

    const command = await screen.findByLabelText("PowerShell command");
    expect((command as HTMLTextAreaElement).value).toContain("pair --access-node-id");
    expect((command as HTMLTextAreaElement).value).not.toContain(authorization.pairing_code);
    expect(screen.getByLabelText(/One-time pairing code/)).toHaveValue(authorization.pairing_code);
    expect(api.createWindowsHelperPairing).toHaveBeenCalledWith("Family laptop");
  });

  it("requires pairing plus an authenticated heartbeat", async () => {
    const onPaired = vi.fn();
    render(<WindowsComputerEnrollment onPaired={onPaired} />);
    fireEvent.click(screen.getByRole("button", { name: "Add / Pair Windows Device" }));
    fireEvent.change(screen.getByLabelText("Computer-friendly name"), { target: { value: "Family laptop" } });
    fireEvent.click(screen.getByRole("button", { name: "Begin Pairing" }));
    fireEvent.click(await screen.findByRole("button", { name: "Check Pairing" }));

    expect(await screen.findByText("Windows computer paired and authenticated.")).toBeInTheDocument();
    expect(onPaired).toHaveBeenCalledTimes(1);
  });
});
