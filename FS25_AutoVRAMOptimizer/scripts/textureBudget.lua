-- ============================================================================
--  Auto VRAM Optimizer  --  Texture-Streaming Budget for Farming Simulator 25
--  Copyright (c) 2026 KeilerHirsch. Licensed under the GNU GPL v3 or later.
--
--  The Man, The Mythos, The Legend : KeilerHirsch
--
--  FS25 caps high-resolution texture streaming at ~4 GB of VRAM by default,
--  which starves texture-heavy and large maps and causes flicker / pop-in.
--  This raises the cap to a value you set once in a plain settings file -- no
--  code editing -- and applies it automatically on every game start.
--
--  Purely client-side rendering: it changes no gameplay, no savegame and no
--  multiplayer state, so it is fully MP-safe and needs no server/client match.
-- ============================================================================

AutoVRAMOptimizer = {}

local MOD = "Auto VRAM Optimizer"
local BYTES_PER_GIB = 1073741824
local DEFAULT_GIB = 6    -- suits an 8 GB card: (VRAM in GB) minus 2 headroom
local MIN_GIB = 2        -- never below the engine's own fallback
local MAX_GIB = 64       -- sanity ceiling against a fat-fingered value

local function log(msg)
    if Logging ~= nil and Logging.info ~= nil then
        Logging.info("[%s] %s", MOD, msg)
    else
        print(("[%s] %s"):format(MOD, msg))
    end
end

local function settingsPath()
    return getUserProfileAppPath() .. "modSettings/FS25_AutoVRAMOptimizer.xml"
end

--- Return the configured budget in GiB, creating a default settings file on the
--- first run so the player edits one clear number instead of Lua code.
local function readConfiguredGiB()
    local path = settingsPath()

    if not fileExists(path) then
        createFolder(getUserProfileAppPath() .. "modSettings")
        local xml = createXMLFile("avo", path, "textureStreamingBudget")
        if xml == nil or xml == 0 then
            -- restricted profile folder, disk full, AV lock, ... : fail safely
            -- to the default instead of writing through an invalid handle.
            log("settings file could not be created; using default")
            return DEFAULT_GIB
        end
        setXMLFloat(xml, "textureStreamingBudget#vramGiB", DEFAULT_GIB)
        setXMLString(xml, "textureStreamingBudget#help",
            "vramGiB = how much graphics-card memory FS25 may use for textures. "
            .. "Rule of thumb: your VRAM in GB minus 2. Only raise above 4 if your "
            .. "card actually has more than 4 GB. Delete this file to reset it.")
        saveXMLFile(xml)
        delete(xml)
        if fileExists(path) then
            log(string.format("created settings %s (default %d GiB)", path, DEFAULT_GIB))
        else
            log("settings file could not be written; using default")
        end
        return DEFAULT_GIB
    end

    local xml = loadXMLFile("avo", path)
    if xml == nil or xml == 0 then
        log("settings file could not be read; using default")
        return DEFAULT_GIB
    end
    local gib = getXMLFloat(xml, "textureStreamingBudget#vramGiB")
    delete(xml)
    if gib == nil then
        log("settings present but vramGiB missing; using default")
        return DEFAULT_GIB
    end
    return gib
end

-- ============================================================================
--  For the curious modder who read this far: rot13 the line below.  ;)
--     Gur ZNA, Gur ZLGU, Gur YRTRAQ; XrvyreUvefpu
-- ============================================================================

function AutoVRAMOptimizer.apply()
    if setTextureStreamingMemoryBudget == nil then
        log("this engine build has no setTextureStreamingMemoryBudget(); nothing to do.")
        return
    end

    local gib = readConfiguredGiB()
    -- A NaN from a corrupt / hand-edited settings file compares false to every
    -- bound, so it would slip past the range clamp below and reach the native
    -- engine call. Reject NaN and infinities up front.
    if gib ~= gib or gib == math.huge or gib == -math.huge then
        gib = DEFAULT_GIB
    end
    if gib < MIN_GIB then gib = MIN_GIB end
    if gib > MAX_GIB then gib = MAX_GIB end

    local bytes = math.floor(gib * BYTES_PER_GIB)
    setTextureStreamingMemoryBudget(bytes)
    log(string.format("texture streaming budget set to %.1f GiB (%d bytes).", gib, bytes))
end

-- Runs once when the mod is loaded (via <extraSourceFiles> in modDesc.xml).
AutoVRAMOptimizer.apply()
