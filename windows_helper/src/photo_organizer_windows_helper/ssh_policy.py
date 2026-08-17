"""Non-connecting validation of effective OpenSSH forwarding policy."""

from __future__ import annotations

import subprocess

from .windows_process import no_window_creation_flags


def verify_ssh_configuration(executable: str, tunnel_arguments: tuple[str, ...]) -> bool:
    """Reject SSH config that would add any forwarding beyond the exact CLI -L."""
    arguments = list(tunnel_arguments)
    try:
        local_index = arguments.index("-L")
    except ValueError:
        return False
    del arguments[local_index : local_index + 2]
    arguments.insert(0, "-G")
    try:
        completed = subprocess.run(
            [executable, *arguments],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
            creationflags=no_window_creation_flags(),
        )
    except (OSError, subprocess.SubprocessError):
        return False

    values: dict[str, list[str]] = {}
    for line in completed.stdout.splitlines():
        key, separator, value = line.partition(" ")
        if separator:
            values.setdefault(key.casefold(), []).append(value.strip())

    if any(values.get(name) for name in ("localforward", "remoteforward", "dynamicforward")):
        return False
    required = {
        "stricthostkeychecking": {"yes", "true"},
        "exitonforwardfailure": {"yes", "true"},
        "gatewayports": {"no", "false"},
        "permitlocalcommand": {"no", "false"},
        "sessiontype": {"none"},
    }
    return all(values.get(name, [""])[0].casefold() in accepted for name, accepted in required.items())
