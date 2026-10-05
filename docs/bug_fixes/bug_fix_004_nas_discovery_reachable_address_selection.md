# Bug Fix 004: NAS Discovery Reachable Address Selection

## Summary

`Discover NAS` found an SMB-advertising NAS and displayed its IP address, but selecting the result populated registration with its `.local` hostname. The browser host could discover that mDNS name while the backend container could not resolve it. Registration therefore failed even though the discovered IPv4 address was reachable on SMB port 445.

The correction keeps discovery limited to NAS devices that advertise `_smb._tcp` through mDNS. It presents enough identity information to distinguish candidates and hands the discovered IPv4 address to registration.

## Bug Found

The observed discovery result represented the same NAS with:

- advertised name: `HENDERSON-NAS`;
- mDNS hostname: `henderson-nas.local`;
- discovered IPv4 address: `192.168.1.171`.

The UI displayed the address but copied `henderson-nas.local` into `NAS hostname or IP address`. From the backend container:

- `henderson-nas.local` failed name resolution;
- `192.168.1.171` was reachable on TCP port 445.

`Prepare registration` consequently failed with `The NAS did not provide bounded SMB identity evidence.` A separate Source Creation validation message, `Choose an available server Source location`, could remain visible and obscure the registration-specific result.

## Why It Worked Before

The earlier successful NAS registrations used `192.168.1.171` directly. They did not depend on the backend container resolving the `.local` name.

The later path started with mDNS discovery. Avahi correctly returned both the advertised hostname and IPv4 address, but the UI selected the hostname rather than the reachable address. This was an address-selection defect, not a change to the NAS, share, credentials, or SMB service.

## Scope Decision

Per Product Owner direction, discovery remains bounded to devices that advertise SMB through `_smb._tcp`. This fix does not scan the local subnet and does not attempt to discover NAS devices that do not advertise SMB. Manual registration remains available for those devices.

## Resolution

- Preserve the advertised NAS name, mDNS hostname, and discovered IPv4 address for each candidate.
- Display all three values in the discovery selector so similarly named devices can be distinguished.
- Populate the registration address with the discovered IPv4 address.
- Keep the advertised name as the suggested friendly NAS name.
- Deduplicate repeated advertisements for the same host without allowing a later IPv6 or duplicate row to replace its usable IPv4 result.
- Ignore malformed addresses, loopback/unspecified addresses, non-IPv4 results, and advertisements not using SMB port 445.
- Sort candidates consistently by advertised name and hostname.
- Clear stale parent Source Creation errors when the operator begins NAS discovery or registration interaction.
- Preserve the existing bounded SMB server-GUID verification during `Prepare registration`; discovery itself creates no durable authority.

## Files Modified

- `scripts/operator/linux/source_identity_broker.py`
- `backend/tests/test_linux_source_access_broker.py`
- `frontend/src/components/NasRegistration.tsx`
- `frontend/src/components/NasRegistration.test.tsx`
- `frontend/src/components/IngestionView.tsx`

## Files Created

- `docs/bug_fixes/bug_fix_004_nas_discovery_reachable_address_selection.md`

## Validation

Automated validation confirmed:

- 37 focused backend broker and NAS-registration tests passed;
- 4 focused NAS-registration UI tests passed;
- multiple SMB-advertising NAS candidates remain visible;
- duplicate advertisements for one hostname produce one candidate;
- IPv4 is retained when Avahi also reports IPv6;
- malformed and non-SMB-port advertisements are excluded;
- the selector shows advertised name, hostname, and IPv4 address;
- selecting a candidate populates registration with its IPv4 address;
- pending registration remains secret-free;
- Source Creation's stale location error is cleared when NAS registration interaction starts;
- frontend lint passed with pre-existing warnings;
- a clean production-style frontend build passed;
- `git diff --check` reported no whitespace errors.

Live discovery after the correction returned:

- advertised name: `HENDERSON-NAS`;
- hostname: `henderson-nas.local`;
- selected registration address: `192.168.1.171`.

The rebuilt development frontend was activated successfully. The hardened broker source is retained in the repository; copying it into the root-owned host service location and restarting that service requires host administrator credentials. The active older broker already returns both hostname and IPv4 address, so the deployed UI correction resolves the observed registration failure while that administrator-controlled installation remains outstanding.

## Operational Note

After deployment, use `Discover NAS`, choose the candidate showing the expected advertised name, hostname, and IP address, and then enter the SMB share. The registered-share label is generated automatically from the NAS and share names. `Prepare registration` will verify the selected address using bounded SMB server-GUID evidence before durable registration can proceed.
