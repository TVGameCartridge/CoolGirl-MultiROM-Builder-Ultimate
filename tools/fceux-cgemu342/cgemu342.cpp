#include "cgemu342.h"

#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <string>

static std::string g_baseDirectory;
static std::string g_chunkName;

static uint32_t rd32(const unsigned char *p)
{
    return (uint32_t)p[0]
        | ((uint32_t)p[1] << 8)
        | ((uint32_t)p[2] << 16)
        | ((uint32_t)p[3] << 24);
}

static uint64_t rd64(const unsigned char *p)
{
    return (uint64_t)rd32(p) | ((uint64_t)rd32(p + 4) << 32);
}

static bool hasContainerFooter(const char *path)
{
    if (!path || !*path) return false;

    FILE *f = fopen(path, "rb");
    if (!f) return false;

    if (_fseeki64(f, 0, SEEK_END) != 0) { fclose(f); return false; }
    const __int64 fileSize = _ftelli64(f);
    if (fileSize < 48) { fclose(f); return false; }
    if (_fseeki64(f, fileSize - 48, SEEK_SET) != 0) { fclose(f); return false; }

    unsigned char footer[48];
    const bool ok = fread(footer, 1, sizeof(footer), f) == sizeof(footer);
    fclose(f);
    if (!ok || memcmp(footer, "CGEMU342", 8) != 0) return false;

    const uint32_t version = rd32(footer + 8);
    const uint32_t count = rd32(footer + 12);
    const uint64_t dirOff = rd64(footer + 16);
    const uint64_t dirSize = rd64(footer + 24);

    if (version != 1 || count < 1) return false;
    if (dirSize < (uint64_t)count * 288ULL) return false;
    if (dirOff > (uint64_t)(fileSize - 48)) return false;
    if (dirSize > (uint64_t)(fileSize - 48) - dirOff) return false;
    return true;
}

void CGEMU342_Init(const char *baseDirectory)
{
    g_baseDirectory = (baseDirectory && *baseDirectory) ? baseDirectory : ".";
    while (!g_baseDirectory.empty() &&
           (g_baseDirectory[g_baseDirectory.size() - 1] == '\\' ||
            g_baseDirectory[g_baseDirectory.size() - 1] == '/'))
        g_baseDirectory.erase(g_baseDirectory.size() - 1);

    g_chunkName = "@" + g_baseDirectory + "\\cgemu342-embedded.lua";
}

bool CGEMU342_IsContainer(const char *path)
{
    return hasContainerFooter(path);
}

const char *CGEMU342_BaseDirectory()
{
    return g_baseDirectory.c_str();
}

const char *CGEMU342_EmbeddedLuaChunkName()
{
    return g_chunkName.c_str();
}

const char *CGEMU342_EmbeddedLuaSource()
{
    static const char source[] = R"CG342(
-- CGEMU342 embedded-container launcher for FCEUX
-- No external games folder required.
--
-- multirom.nes layout appended by coolgirl-combiner-emu:
--   [payload files]
--   [288-byte directory entries]
--   footer:
--     "CGEMU342" 8 bytes
--     version     u32 LE
--     count       u32 LE
--     dir_offset  u64 LE
--     dir_size    u64 LE
--     payload_start u64 LE
--     reserved    u64 LE
--
-- Menu mailbox:
--   $07F0 = game ID low
--   $07F1 = game ID high
--   $07F2 = $A5 launch
--
-- R = return to multirom menu.

local ROOT
do
    local src = debug.getinfo(1, "S").source or ""
    if src:sub(1,1) == "@" then src = src:sub(2) end
    ROOT = src:match("^(.*[\\/])") or ".\\"
end

local MENU_ROM = ROOT .. "multirom.nes"
local TEMP = os.getenv("TEMP") or ROOT
local CACHE_DIR = TEMP .. "\\CGEMU342"
os.execute('cmd /c if not exist "' .. CACHE_DIR .. '" mkdir "' .. CACHE_DIR .. '" >nul 2>nul')

local function read_u16_le(s, p)
    local b1,b2 = s:byte(p,p+1)
    return (b1 or 0) + (b2 or 0) * 256
end

local function read_u32_le(s, p)
    local b1,b2,b3,b4 = s:byte(p,p+3)
    return (b1 or 0)
        + (b2 or 0) * 256
        + (b3 or 0) * 65536
        + (b4 or 0) * 16777216
end

local function read_u64_le(s, p)
    local lo = read_u32_le(s, p)
    local hi = read_u32_le(s, p + 4)
    return lo + hi * 4294967296
end

local function read_cstr(s)
    local z = s:find("\0", 1, true)
    if z then return s:sub(1,z-1) end
    return s
end

local function load_directory()
    local f = io.open(MENU_ROM, "rb")
    if not f then return nil, "multirom.nes not found" end

    local size = f:seek("end")
    if not size or size < 48 then
        f:close()
        return nil, "multirom too small"
    end

    f:seek("set", size - 48)
    local footer = f:read(48)
    if not footer or #footer ~= 48 or footer:sub(1,8) ~= "CGEMU342" then
        f:close()
        return nil, "CGEMU342 footer missing"
    end

    local version = read_u32_le(footer, 9)
    local count = read_u32_le(footer, 13)
    local dir_off = read_u64_le(footer, 17)
    local dir_size = read_u64_le(footer, 25)

    if version ~= 1 then
        f:close()
        return nil, "unsupported container version"
    end

    if count < 1 or dir_off < 0 or dir_size < count * 288
       or dir_off + dir_size > size - 48 then
        f:close()
        return nil, "invalid CGEMU342 directory"
    end

    local entries = {}
    f:seek("set", dir_off)

    for i=0,count-1 do
        local e = f:read(288)
        if not e or #e ~= 288 then
            f:close()
            return nil, "truncated directory"
        end

        local off = read_u64_le(e, 1)
        local len = read_u64_le(e, 9)
        local fmt = read_u16_le(e, 17)
        local mapper = read_u16_le(e, 19)
        local submapper = read_u16_le(e, 21)
        local title = read_cstr(e:sub(25, 152))
        local board = read_cstr(e:sub(153, 280))

        entries[i+1] = {
            offset=off,
            size=len,
            format=fmt,
            mapper=mapper,
            submapper=submapper,
            title=title,
            board=board
        }
    end

    f:close()
    return entries
end

local entries = nil

local function refresh_directory()
    entries = load_directory()
    return entries ~= nil
end

local function safe_name(s)
    s = tostring(s or "game")
    s = s:gsub('[<>:"/\\|%?%*]', "_")
    if s == "" then s = "game" end
    return s
end

local function extract_game(id)
    if not entries and not refresh_directory() then return nil end

    local e = entries[id + 1]
    if not e then return nil end

    local ext = ".nes"
    if e.format == 3 then ext = ".unf" end

    local out = CACHE_DIR .. "\\" .. string.format("%03d_", id) .. safe_name(e.title) .. ext

    local src = io.open(MENU_ROM, "rb")
    if not src then return nil end
    src:seek("set", e.offset)

    local dst = io.open(out, "wb")
    if not dst then
        src:close()
        return nil
    end

    local left = e.size
    while left > 0 do
        local want = math.min(left, 65536)
        local chunk = src:read(want)
        if not chunk or #chunk == 0 then
            dst:close()
            src:close()
            return nil
        end
        dst:write(chunk)
        left = left - #chunk
    end

    dst:close()
    src:close()
    return out
end

refresh_directory()

local launch_guard = false
local r_was_down = false

while true do
    local keys = input.get() or {}
    local r_down = keys.R == true

    if r_down and not r_was_down then
        emu.loadrom(MENU_ROM)
        refresh_directory()
        launch_guard = false
    end
    r_was_down = r_down

    local magic = memory.readbyte(0x07F2)

    if magic == 0xA5 and not launch_guard then
        launch_guard = true

        local lo = memory.readbyte(0x07F0)
        local hi = memory.readbyte(0x07F1)
        local id = lo + hi * 256

        memory.writebyte(0x07F2, 0)

        local romfile = extract_game(id)
        if romfile then
            emu.loadrom(romfile)
        end

        launch_guard = false
    elseif magic ~= 0xA5 then
        launch_guard = false
    end

    emu.frameadvance()
end

)CG342";
    return source;
}
