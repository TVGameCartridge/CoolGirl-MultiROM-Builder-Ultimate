#include "cgemu342.h"
#include "types.h"
#include "x6502.h"

#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <string>

static std::string g_menuPath;
static std::string g_pendingPath;
static bool g_menuActive = false;
static bool g_launchGuard = false;
static bool g_rWasDown = false;

static uint16_t rd16(const unsigned char *p)
{
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

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

static bool readFooter(const char *path, uint32_t &count, uint64_t &dirOff, uint64_t &dirSize)
{
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
    if (rd32(footer + 8) != 1) return false;

    count = rd32(footer + 12);
    dirOff = rd64(footer + 16);
    dirSize = rd64(footer + 24);

    if (count < 1) return false;
    if (dirSize < (uint64_t)count * 288ULL) return false;
    if (dirOff > (uint64_t)(fileSize - 48)) return false;
    if (dirSize > (uint64_t)(fileSize - 48) - dirOff) return false;
    return true;
}

static std::string safeName(const unsigned char *p, size_t n)
{
    std::string s;
    for (size_t i = 0; i < n && p[i]; ++i)
    {
        char c = (char)p[i];
        if ((unsigned char)c < 32 || strchr("<>:\"/\\|?*", c)) c = '_';
        s += c;
    }
    while (!s.empty() && (s[s.size() - 1] == ' ' || s[s.size() - 1] == '.')) s.erase(s.size() - 1);
    return s.empty() ? "game" : s;
}

static bool extractGame(unsigned id, std::string &out)
{
    uint32_t count = 0;
    uint64_t dirOff = 0, dirSize = 0;
    if (g_menuPath.empty() || !readFooter(g_menuPath.c_str(), count, dirOff, dirSize) || id >= count)
        return false;

    FILE *src = fopen(g_menuPath.c_str(), "rb");
    if (!src) return false;

    const uint64_t entryPos = dirOff + (uint64_t)id * 288ULL;
    if (_fseeki64(src, (__int64)entryPos, SEEK_SET) != 0) { fclose(src); return false; }

    unsigned char entry[288];
    if (fread(entry, 1, sizeof(entry), src) != sizeof(entry)) { fclose(src); return false; }

    const uint64_t payloadOff = rd64(entry + 0);
    const uint64_t payloadLen = rd64(entry + 8);
    const uint16_t format = rd16(entry + 16);

    if (_fseeki64(src, 0, SEEK_END) != 0) { fclose(src); return false; }
    const __int64 fileSizeSigned = _ftelli64(src);
    if (fileSizeSigned < 0) { fclose(src); return false; }
    const uint64_t fileSize = (uint64_t)fileSizeSigned;
    if (payloadOff > fileSize || payloadLen > fileSize - payloadOff) { fclose(src); return false; }

    char tempPath[MAX_PATH + 1] = {0};
    DWORD n = GetTempPathA(MAX_PATH, tempPath);
    if (n == 0 || n > MAX_PATH) { fclose(src); return false; }

    std::string cacheDir = std::string(tempPath) + "CGEMU342";
    if (!CreateDirectoryA(cacheDir.c_str(), NULL) && GetLastError() != ERROR_ALREADY_EXISTS)
    {
        fclose(src);
        return false;
    }

    char prefix[32];
    sprintf(prefix, "%03u_", id);
    out = cacheDir + "\\" + prefix + safeName(entry + 24, 128) + (format == 3 ? ".unf" : ".nes");

    if (_fseeki64(src, (__int64)payloadOff, SEEK_SET) != 0) { fclose(src); return false; }
    FILE *dst = fopen(out.c_str(), "wb");
    if (!dst) { fclose(src); return false; }

    unsigned char buffer[65536];
    uint64_t left = payloadLen;
    bool ok = true;
    while (left)
    {
        const size_t want = left > sizeof(buffer) ? sizeof(buffer) : (size_t)left;
        const size_t got = fread(buffer, 1, want, src);
        if (got != want || fwrite(buffer, 1, got, dst) != got)
        {
            ok = false;
            break;
        }
        left -= got;
    }

    fclose(dst);
    fclose(src);
    if (!ok)
    {
        DeleteFileA(out.c_str());
        out.clear();
        return false;
    }
    return true;
}

void CGEMU342_Init(const char *baseDirectory)
{
    g_menuPath.clear();
    g_pendingPath.clear();
    g_menuActive = false;
    g_launchGuard = false;
    g_rWasDown = false;

    if (baseDirectory && *baseDirectory)
    {
        g_menuPath = baseDirectory;
        const char last = g_menuPath.empty() ? 0 : g_menuPath[g_menuPath.size() - 1];
        if (last != '\\' && last != '/') g_menuPath += "\\";
        g_menuPath += "multirom.nes";
    }
}

void CGEMU342_OnRomLoaded(const char *name)
{
    uint32_t count = 0;
    uint64_t dirOff = 0, dirSize = 0;
    if (name && readFooter(name, count, dirOff, dirSize))
    {
        g_menuPath = name;
        g_menuActive = true;
        g_launchGuard = false;
    }
    else
    {
        g_menuActive = false;
        g_launchGuard = false;
    }
}

void CGEMU342_Poll()
{
    const bool rDown = (GetAsyncKeyState('R') & 0x8000) != 0;
    if (rDown && !g_rWasDown && !g_menuPath.empty())
    {
        DWORD attrs = GetFileAttributesA(g_menuPath.c_str());
        if (attrs != INVALID_FILE_ATTRIBUTES && !(attrs & FILE_ATTRIBUTE_DIRECTORY))
        {
            g_pendingPath = g_menuPath;
            g_menuActive = false;
            g_launchGuard = false;
        }
    }
    g_rWasDown = rDown;

    if (!g_menuActive || !g_pendingPath.empty()) return;

    const uint8 magic = X6502_DMR(0x07F2);
    if (magic == 0xA5 && !g_launchGuard)
    {
        g_launchGuard = true;
        const unsigned id = (unsigned)X6502_DMR(0x07F0) | ((unsigned)X6502_DMR(0x07F1) << 8);
        X6502_DMW(0x07F2, 0);

        std::string extracted;
        if (extractGame(id, extracted))
        {
            g_pendingPath = extracted;
            g_menuActive = false;
        }
    }
    else if (magic != 0xA5)
    {
        g_launchGuard = false;
    }
}

bool CGEMU342_TakePendingLoad(std::string &path)
{
    if (g_pendingPath.empty()) return false;
    path = g_pendingPath;
    g_pendingPath.clear();
    return true;
}
