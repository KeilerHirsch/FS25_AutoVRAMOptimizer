# Changelog

All notable changes to **Auto VRAM Optimizer** are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.1.2.0] - 2026-07-17

### Fixed
- **Recommended-budget floor could exceed the card's physical VRAM on very
  small GPUs.** `recommended_budget_gib()`'s `floor_gib=2.0` was applied
  unconditionally, so a 1 GiB integrated GPU received a 2.0 GiB budget (200%
  of its VRAM) and a 2 GiB card received exactly 100%, defeating the 75%
  fraction cap the floor sits on top of. The floor is now itself capped at
  that fraction, so it never wins on a card small enough for it to matter.
  Only 1-2 GiB inputs change (now 0.75 / 1.5 GiB respectively); every card
  from 3 GiB up is unaffected (verified by re-running the formula across the
  full 1-64 GiB range).
- **`Auto-Set-VRAM`'s console message described the wrong formula.** It said
  "VRAM minus 2 GiB headroom" — stale since 1.1.1.0 introduced the 3 GiB /
  75%-cap formula. A user reading "minus 2", seeing 5.0 GiB on an 8 GB card,
  and concluding the tool was wrong could "fix" it by hand-editing the
  settings file back to the old (crash-prone) 6.0 GiB value. The message now
  states the actual formula and is generated from the same constants the
  formula uses, so it cannot drift out of sync again.

### Added
- **Settings file now records which formula version produced it
  (`formulaGen`).** Previously a value written by an earlier, less
  conservative tool release (e.g. `6.0` from the pre-1.1.1.0 formula) was
  indistinguishable from a value the user set by hand, and nothing —
  including this fix — could ever correct it automatically, because the mod
  only writes a value when the settings file is missing. `formulaGen` makes
  that provenance visible for manual inspection and for any future tool
  version that wants to check it — this release does not yet reconcile an
  old value automatically. **If you installed this mod before 1.1.1.0**,
  your settings file may still hold the old formula's value: delete
  `<FS25 profile>/modSettings/FS25_AutoVRAMOptimizer.xml` (or re-run
  `Auto-Set-VRAM`) to have it recomputed under the current formula.

## [1.1.1.1] - 2026-07-15

### Fixed
- **`Auto-Set-VRAM.bat` no longer changes the caller's console codepage.** The
  launcher switched the console to UTF-8 (`chcp 65001`) without restoring it —
  `chcp` is console state that `endlocal` does **not** revert, so running the tool
  from an existing terminal (rather than a double-click) left that terminal stuck
  on codepage 65001. It now records the current codepage, switches to UTF-8 only
  around the Python run, and restores it afterwards; the early "missing Python /
  script" exits stay on the original codepage (their messages are ASCII).

### Changed
- **Mod version bumped to 1.1.1.1 in lockstep with the tool** — the in-game Lua and
  the settings format are **behaviourally identical** to 1.1.1.0 (no gameplay/VRAM
  change); only `modDesc.xml` `<version>` moves, so the tool and the mod carry the
  same version and the dedicated server + clients update together in one step.

## [1.1.1.0] - 2026-07-15

### Changed
- **Safer default budget — bigger VRAM headroom.** The recommended/blind-default
  texture budget now reserves **3 GiB** of headroom instead of 2, and never claims
  more than **75%** of the card. An 8 GB card now gets **5 GiB** (was 6). The old
  2 GiB headroom left too little for the game's non-texture VRAM (render targets,
  meshes, shadow maps, other mods) and could exhaust VRAM and crash the client while
  streaming a large/heavy modded map — observed on an 8 GB card. The settings file
  stays player-editable; lower it further if a very heavy map still crashes.

### Notes
- Existing installs keep whatever value is already in `modSettings/FS25_AutoVRAMOptimizer.xml`.
  Delete that file to regenerate it with the new, safer default.

## [1.1.0.0] - 2026-07-14

### Added
- **True cross-vendor VRAM auto-detection.** A one-click helper (`Auto-Set-VRAM.bat`
  → `configure_vram.py`, shipped in `AutoVRAM-Tool.zip`) detects your graphics-card
  memory on **NVIDIA / AMD / Intel** — via the vendor-neutral display-adapter registry
  key `HardwareInformation.qwMemorySize` (not the 4 GB-capped WMI value), with an
  `nvidia-smi` fallback — and writes the matched budget into the mod's settings file.
  The mod previously only auto-*applied* a hardcoded 6 GiB default; now the "Auto" in
  the name is real. Detector is reused (verified) from the 16x Map Fix tool.
- CI now runs the tool's Python unit tests (stdlib `unittest`, no deps) alongside the
  Lua parse check; least-privilege `permissions: contents: read` on the workflow.

### Notes
- The mod still works standalone with its safe default if you don't run the helper —
  the tool is an optional one-time step (needs Windows + Python 3).

## [1.0.3.0] - 2026-07-12

### Changed
- Relicensed **back to GPLv3**, restoring the original license. The KeilerHirsch
  default is GPLv3 (open but copyleft: forks/PRs welcome, keep the attribution and
  the same license). Reverts the brief v1.0.2.0 proprietary switch.

## [1.0.2.0] - 2026-07-12

### Changed
- Relicensed to **Proprietary, source-available** (was GPLv3), consistent with the
  KeilerHirsch mod standard. Prior releases (≤ v1.0.1.0) remain under GPLv3; this
  change applies from this release onward.
- Added the author signature to the script header and shipped `LICENSE` inside the
  mod zip.

### Added
- Ko-fi support callout in the README (FUNDING already present).

## [1.0.1.0] - 2026-07-11

Robustness-hardening pass (independent code- and security-review, luac).
No change to normal behaviour; every fix hardens the first-run and
settings-parsing paths that run on every mod load.

### Fixed
- Reject a NaN or infinite `vramGiB` from a corrupt or hand-edited settings
  file before it can slip past the range clamp (NaN compares false to every
  bound) and reach the native `setTextureStreamingMemoryBudget` call.
- Guard the first-run settings-file creation against a failed `createXMLFile`
  (restricted profile folder, disk full, AV lock): fail safely to the default
  instead of writing through an invalid handle — mirrors the existing guard on
  the load path.
- Verify the settings file was actually written before logging "created".

## [1.0.0.0] - 2026-07-11

### Added
- Initial release. Raises FS25's ~4 GB texture-streaming VRAM cap to a value
  set once in `modSettings/FS25_AutoVRAMOptimizer.xml` (default 6 GiB, clamped
  2–64), applied automatically on every game start. Purely client-side,
  multiplayer-safe. GPLv3, localized in 8 languages.

[1.0.1.0]: https://github.com/KeilerHirsch/FS25_AutoVRAMOptimizer/releases/tag/v1.0.1.0
[1.0.0.0]: https://github.com/KeilerHirsch/FS25_AutoVRAMOptimizer/releases/tag/v1.0.0.0
