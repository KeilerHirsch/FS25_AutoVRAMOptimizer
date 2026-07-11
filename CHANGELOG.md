# Changelog

All notable changes to **Auto VRAM Optimizer** are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
