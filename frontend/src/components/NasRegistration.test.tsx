import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";
import NasRegistration from "./NasRegistration";


vi.mock("@/lib/api", () => ({
  createNasPendingRegistration: vi.fn(),
  discoverNasAppliances: vi.fn(),
  getNasRegistrations: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.getNasRegistrations).mockResolvedValue({
    registrations: [{
      appliance_id: "11111111-1111-4111-8111-111111111111",
      share_id: "22222222-2222-4222-8222-222222222222",
      appliance_name: "Photo Organizer NAS",
      location_name: "Photo Organizer NAS",
      share_name: "PhotoOrganizer",
      location_id: "linux-nas-photo-organizer",
      registration_status: "registered",
      availability: "available",
      status_message: "Registered NAS location is available.",
      source_endpoint_id: 1,
    }],
  });
  vi.mocked(api.discoverNasAppliances).mockResolvedValue({
    status: "completed",
    candidates: [{
      candidate_id: "sha256:candidate",
      suggested_name: "Family NAS",
      network_host: "family-nas.local",
      address_hint: "192.0.2.10",
    }],
    manual_entry_available: true,
    messages: [],
  });
  vi.mocked(api.createNasPendingRegistration).mockResolvedValue({
    registration_id: "33333333-3333-4333-8333-333333333333",
    state: "pending",
    appliance_name: "Family NAS",
    location_name: "Family Photos",
    share_name: "Photos",
    server_guid_masked: "sha256:…123456789abc",
    reuses_registered_appliance: false,
    operation: "create_share",
    expires_at: "2030-01-01T00:00:00Z",
    operator_command: "sudo /usr/local/lib/photo-organizer/register-nas-location.py install --registration-id 33333333-3333-4333-8333-333333333333",
    messages: [],
  });
});

afterEach(cleanup);

describe("NAS registration", () => {
  it("shows the current registration and keeps manual registration available", async () => {
    render(<NasRegistration onLocationsChanged={vi.fn()} />);
    expect(await screen.findByText("Photo Organizer NAS — Photo Organizer NAS")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Register NAS manually" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Discover NAS" })).toBeInTheDocument();
  });

  it("uses discovery only to seed a secret-free pending registration", async () => {
    render(<NasRegistration onLocationsChanged={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Discover NAS" }));
    fireEvent.change(await screen.findByLabelText("Discovered NAS (optional)"), {
      target: { value: "sha256:candidate" },
    });
    fireEvent.change(screen.getByLabelText("SMB share name"), { target: { value: "Photos" } });
    fireEvent.change(screen.getByLabelText("Photo location name"), { target: { value: "Family Photos" } });
    fireEvent.click(screen.getByRole("button", { name: "Prepare registration" }));
    expect(await screen.findByText(/sudo \/usr\/local\/lib\/photo-organizer\/register-nas-location.py/)).toBeInTheDocument();
    expect(api.createNasPendingRegistration).toHaveBeenCalledWith({
      network_host: "family-nas.local",
      appliance_name: "Family NAS",
      share_name: "Photos",
      location_name: "Family Photos",
    });
    const payload = JSON.stringify(vi.mocked(api.createNasPendingRegistration).mock.calls);
    expect(payload).not.toContain("password");
    expect(payload).not.toContain("credential");
  });

  it("offers manual entry when discovery returns no candidates", async () => {
    vi.mocked(api.discoverNasAppliances).mockResolvedValue({
      status: "completed",
      candidates: [],
      manual_entry_available: true,
      messages: [],
    });
    render(<NasRegistration onLocationsChanged={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Discover NAS" }));
    expect(await screen.findByLabelText("NAS hostname or IP address")).toBeInTheDocument();
    expect(screen.getByText("No NAS was discovered. Enter its hostname manually.")).toBeInTheDocument();
  });

  it("keeps unavailable and identity-conflict registrations visible", async () => {
    vi.mocked(api.getNasRegistrations).mockResolvedValue({
      registrations: [
        {
          appliance_id: "11111111-1111-4111-8111-111111111111",
          share_id: "22222222-2222-4222-8222-222222222222",
          appliance_name: "Offline NAS",
          location_name: "Archive",
          share_name: "Archive",
          location_id: "linux-nas-offline",
          registration_status: "registered",
          availability: "unavailable",
          status_message: "Registered NAS location is not currently available.",
          source_endpoint_id: 2,
        },
        {
          appliance_id: "33333333-3333-4333-8333-333333333333",
          share_id: "44444444-4444-4444-8444-444444444444",
          appliance_name: "Conflict NAS",
          location_name: "Photos",
          share_name: "Photos",
          location_id: "linux-nas-conflict",
          registration_status: "registered",
          availability: "identity_conflict",
          status_message: "Registered NAS identity conflicts with current host evidence.",
          source_endpoint_id: 3,
        },
      ],
    });
    render(<NasRegistration onLocationsChanged={vi.fn()} />);
    expect(await screen.findByText("Offline NAS — Archive")).toBeInTheDocument();
    expect(screen.getByText("Conflict NAS — Photos")).toBeInTheDocument();
    expect(screen.getByText(/identity conflict/)).toBeInTheDocument();
  });
});
