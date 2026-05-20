"""subprocess wrapper with sane defaults — never raises, returns empty on failure."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence


def run(cmd: str | Sequence[str], timeout: int = 8) -> str:
    try:
        result = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        return ""
