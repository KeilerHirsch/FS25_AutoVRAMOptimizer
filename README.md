<div align="center">

<img src="assets/logo_512.png" width="220" alt="Auto VRAM Optimizer"/>

# Auto VRAM Optimizer

**Raise Farming Simulator 25's texture-streaming VRAM budget — automatically.**

[![License: Proprietary, source-available](https://img.shields.io/badge/License-Proprietary%20source--available-blue.svg)](LICENSE) &nbsp;·&nbsp; FS25 &nbsp;·&nbsp; Multiplayer-safe &nbsp;·&nbsp; 8 languages

</div>

> [!IMPORTANT]
> Enjoying the mod? You can support development on **[Ko-fi](https://ko-fi.com/keilerhirsch)** ☕ — please mention *Auto VRAM Optimizer* so I know what to keep building.

---

## What it does

Farming Simulator 25 caps high-resolution **texture streaming at about 4 GB of graphics memory** by default. On texture-heavy or large maps your card constantly drops and reloads textures → **flicker, pop-in, and stutter during load**.

**Auto VRAM Optimizer** raises that cap automatically on every game start, so FS25 actually uses the VRAM your card has. The result: **smoother loading and crisp textures** — no code editing, no fuss.

## Why you want it

- ✅ **Smoother loading** — fewer "not responding" hangs on big maps
- ✅ **No texture pop-in / flicker** when you turn the camera
- ✅ **Multiplayer-safe** — changes no gameplay, no savegame, no sync state
- ✅ **Set-and-forget** — sensible default, one value to tweak if needed
- ✅ **8 languages** — shows in your game's language automatically (EN/DE/FR/ES/IT/PT/PL/RU)

## Requirements

> [!IMPORTANT]
> Only use it if your graphics card has **more than 4 GB of VRAM**.

## Install

1. Download `FS25_AutoVRAMOptimizer.zip`.
2. Drop it into your FS25 `mods` folder.
3. Enable it in the mod selection. Done — it applies on every start.

## Configure (optional)

On first run it creates `modSettings/FS25_AutoVRAMOptimizer.xml`:

```xml
<textureStreamingBudget vramGiB="6.0" .../>
```

`vramGiB` = how much VRAM FS25 may use for textures. **Rule of thumb: your VRAM in GB minus 2.** The default (`6`) suits 8 GB cards. Set it once for your card; delete the file to reset.

| Your card | Suggested `vramGiB` |
|---|---|
| 6 GB | `4` |
| 8 GB | `6` (default) |
| 12 GB | `10` |
| 16 GB | `14` |
| 24 GB | `22` |

## How it works

FS25 exposes an engine call, `setTextureStreamingMemoryBudget(bytes)`, that most players never touch — and its default is a conservative ~4 GB. This mod calls it once on load with your configured value. That's the whole trick: honest, tiny, and it just works.

## Multiplayer

Fully safe. The texture budget is a **local rendering setting** — it never touches gameplay, savegames, or server/client sync. Install it (or not) per machine; nothing has to match.

## Roadmap

- In-game settings slider (pick your VRAM without touching a file)

## License

**Proprietary, source-available** — see [LICENSE](LICENSE). You may read the source and use the released mod unmodified; you may not copy, modify, or redistribute it. Only ModHub and this repository are valid sources.

## Credits

Built by **KeilerHirsch**.
_There's a little something in the source for modders who read that far. 😉_
