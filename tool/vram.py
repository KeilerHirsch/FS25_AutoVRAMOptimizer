#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Auto VRAM Optimizer -- cross-vendor GPU VRAM detection (Windows)
#  "The Man, The Mythos, The Legend : KeilerHirsch"   (GNU GPL v3 or later)
#
#  Reports the primary graphics card's physical video memory so the mod's
#  texture-streaming budget can be set from real hardware instead of a
#  guessed constant.
#
#  Primary source is the display-adapter class registry key -- a vendor-neutral
#  value that NVIDIA, AMD and Intel drivers all populate, and which (unlike WMI
#  Win32_VideoController.AdapterRAM) is NOT capped at 4 GB:
#
#    HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-...}\<NNNN>\
#        HardwareInformation.qwMemorySize
#
#  It is read for every adapter and the maximum is taken, which picks the
#  discrete GPU over an integrated one. The value may be stored as a REG_QWORD
#  (an int) or as a REG_BINARY blob (little-endian bytes); both are handled.
#  If the registry yields nothing, nvidia-smi is tried; if that also fails the
#  caller falls back to its own default.
"""Cross-vendor GPU VRAM detection for Windows (NVIDIA / AMD / Intel)."""

from __future__ import annotations

import subprocess  # nosec B404 -- only runs nvidia-smi with a fixed list-form argv (no shell); see nvidia_smi_vram_bytes
from typing import NamedTuple

#: Windows "Display adapters" device class.
DISPLAY_CLASS_KEY = (
    r"SYSTEM\CurrentControlSet\Control\Class"
    r"\{4d36e968-e325-11ce-bfc1-08002be10318}"
)

#: Preferred first (uncapped 64-bit), then the legacy 32-bit fallback.
_MEMORY_PROPERTIES = (
    "HardwareInformation.qwMemorySize",
    "HardwareInformation.MemorySize",
)

_BYTES_PER_GIB = 1024 ** 3
_BYTES_PER_MIB = 1024 ** 2
_NVIDIA_SMI_TIMEOUT_S = 10

#: recommended_budget_gib() defaults, exposed so configure_vram.py's status
#: message can describe the actual formula instead of a hand-copied string
#: that silently goes stale the next time these numbers change.
HEADROOM_GIB_DEFAULT = 3.0
FLOOR_GIB_DEFAULT = 2.0
MAX_FRACTION_DEFAULT = 0.75

#: Bumped whenever recommended_budget_gib()'s formula changes. Written into
#: the settings XML (see configure_vram.write_settings) so a value already on
#: disk from an older tool version is distinguishable from one a user set by
#: hand -- without this, a stale pre-fix value survives every mod/tool update
#: forever, because the mod only writes a default when the file is missing.
FORMULA_GEN = 2


def _coerce_positive_int(value: object) -> int | None:
    """Coerce a winreg value to a positive int.

    The memory size may arrive as an ``int`` (REG_QWORD/REG_DWORD) or as raw
    little-endian ``bytes`` (REG_BINARY) depending on the driver -- an integrated
    GPU on the same machine was observed storing it as REG_BINARY while the
    discrete card used REG_QWORD. Anything else, or a non-positive result, is
    treated as "unknown".
    """
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, (bytes, bytearray)):
        number = int.from_bytes(value, "little")
        return number if number > 0 else None
    return None


def registry_vram_bytes() -> int:
    """Largest adapter VRAM (bytes) recorded in the registry, or 0 if none.

    Returns 0 on non-Windows hosts (no ``winreg``) or if nothing is readable.
    """
    try:
        import winreg  # Windows-only; imported lazily so the module loads anywhere
    except ImportError:
        return 0

    best = 0
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, DISPLAY_CLASS_KEY) as root:
            index = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(root, index)
                except OSError:
                    break  # no more subkeys
                index += 1
                if not subkey_name.isdigit():  # adapters are 0000, 0001, ...
                    continue
                try:
                    with winreg.OpenKey(root, subkey_name) as adapter:
                        for prop in _MEMORY_PROPERTIES:
                            try:
                                raw, _ = winreg.QueryValueEx(adapter, prop)
                            except OSError:
                                continue
                            size = _coerce_positive_int(raw)
                            if size is not None:
                                best = max(best, size)
                                break  # prefer qwMemorySize over MemorySize
                except OSError:
                    continue
    except OSError:
        return 0
    return best


def nvidia_smi_vram_bytes() -> int:
    """Total VRAM (bytes) of the largest NVIDIA GPU via nvidia-smi, or 0."""
    try:
        result = subprocess.run(  # nosec B603 B607 -- nvidia-smi is a standard system tool resolved via PATH; fixed list-form argv, no shell, no untrusted input
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=_NVIDIA_SMI_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return 0
    if result.returncode != 0:
        return 0
    best = 0
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.isdigit():  # value is in MiB
            best = max(best, int(line) * _BYTES_PER_MIB)
    return best


def detect_vram_bytes() -> int:
    """Best-effort physical VRAM of the primary GPU, in bytes (0 if unknown)."""
    return registry_vram_bytes() or nvidia_smi_vram_bytes()


def detect_vram_gib() -> float | None:
    """Detected VRAM in GiB, or ``None`` if it could not be determined."""
    raw = detect_vram_bytes()
    return raw / _BYTES_PER_GIB if raw else None


class BudgetBreakdown(NamedTuple):
    """The intermediate values behind :func:`recommended_budget_gib`.

    Exists so a status message can describe *why* a budget was chosen using
    the exact numbers that produced it, instead of a hand-written formula
    description living in a different module -- two copies of the same
    formula (one computing, one describing in prose) is how the budget and
    its own status message went out of sync in earlier releases.
    """

    rounded: int
    by_headroom: float
    by_fraction: float
    budget: float


def budget_breakdown(
    vram_gib: float,
    headroom_gib: float = HEADROOM_GIB_DEFAULT,
    floor_gib: float = FLOOR_GIB_DEFAULT,
    max_fraction: float = MAX_FRACTION_DEFAULT,
) -> BudgetBreakdown:
    """Compute :func:`recommended_budget_gib` and its intermediate values.

    ``max_fraction`` of the (rounded) card is the hard ceiling; ``floor_gib``
    and ``headroom_gib`` only decide where under that ceiling the budget
    lands. This is the ``min(ceiling, max(floor, by_headroom))`` form of the
    same formula documented on :func:`recommended_budget_gib` -- verified
    equivalent to the floor-capped ``max(min(floor, ceiling), min(by_headroom,
    ceiling))`` form by exhaustive comparison over 200k random inputs
    (2026-07-17), not just algebra.

    The final result is also capped at the *raw, unrounded* ``vram_gib`` --
    without this, a sub-1-GiB card gets rounded UP to a whole GiB before the
    ceiling is computed (this rounding exists so a real card reporting
    slightly under its nominal size, e.g. 7.9961 GiB, is treated as the 8 GiB
    it actually is), and the ceiling is then a fraction of that rounded-up
    value rather than of the card that's actually there. A 0.51 GiB card
    would otherwise get 0.75 GiB (147% of it) -- worse than the very
    iGPU-overshoot bug this cap exists to fix.
    """
    rounded = round(vram_gib)
    by_headroom = rounded - headroom_gib
    by_fraction = rounded * max_fraction
    budget = min(by_fraction, max(floor_gib, by_headroom))
    budget = min(budget, vram_gib)
    return BudgetBreakdown(rounded, by_headroom, by_fraction, float(budget))


def recommended_budget_gib(
    vram_gib: float,
    headroom_gib: float = HEADROOM_GIB_DEFAULT,
    floor_gib: float = FLOOR_GIB_DEFAULT,
    max_fraction: float = MAX_FRACTION_DEFAULT,
) -> float:
    """Texture-streaming budget for the given VRAM.

    Rounds the (slightly-under-nominal) reported VRAM to the nearest whole GiB,
    then takes the SMALLER of two safety limits, never dropping below an
    *effective* floor:

    * a fixed ``headroom_gib`` reserved for the OS/desktop and -- decisively --
      for the game's own non-texture VRAM (render targets, meshes, shadow maps
      and other mods' assets), which on a large/heavy map is another 2-3 GB on
      top of the texture budget;
    * a ``max_fraction`` ceiling so the budget never claims more than that share
      of the card (guards small cards where a flat headroom is too generous).

    An 8 GB card (~7.99 GiB reported) therefore yields 5 GiB. Earlier releases
    reserved only 2 GiB and returned 6 GiB, which could exhaust VRAM and crash
    the client while streaming a heavy modded map (observed: 8 GB card + a large
    map + big modpack). 5 GiB leaves ~3 GB for everything else.

    ``max_fraction`` is the hard ceiling; ``floor_gib`` never raises the
    budget above it. Earlier code applied ``floor_gib`` unconditionally,
    giving a 1 GiB iGPU a budget at 200% of its physical VRAM (2 GiB card:
    100%) -- the exact small-card case ``max_fraction`` exists to guard,
    defeated by the floor sitting on top of it.
    """
    return budget_breakdown(vram_gib, headroom_gib, floor_gib, max_fraction).budget


if __name__ == "__main__":
    gib = detect_vram_gib()
    if gib is None:
        print("VRAM: not detected")
    else:
        print(f"VRAM: {gib:.2f} GiB  ->  recommended texture budget "
              f"{recommended_budget_gib(gib):.1f} GiB")
