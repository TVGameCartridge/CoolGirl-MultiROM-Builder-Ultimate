#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("emu-ex-plus-alpha")
MAIN = ROOT / "NES.emu/src/main/Main.cc"

text = MAIN.read_text(encoding="utf-8")


def replace_function(src: str, signature_prefix: str, replacement: str) -> str:
    start = src.find(signature_prefix)
    if start < 0:
        raise RuntimeError(f"function not found: {signature_prefix}")
    brace = src.find("{", start)
    if brace < 0:
        raise RuntimeError(f"opening brace not found: {signature_prefix}")
    depth = 0
    i = brace
    in_string = False
    in_char = False
    escape = False
    line_comment = False
    block_comment = False
    while i < len(src):
        c = src[i]
        n = src[i + 1] if i + 1 < len(src) else ""
        if line_comment:
            if c == "\n":
                line_comment = False
        elif block_comment:
            if c == "*" and n == "/":
                block_comment = False
                i += 1
        elif in_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
        elif in_char:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == "'":
                in_char = False
        else:
            if c == "/" and n == "/":
                line_comment = True
                i += 1
            elif c == "/" and n == "*":
                block_comment = True
                i += 1
            elif c == '"':
                in_string = True
            elif c == "'":
                in_char = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    return src[:start] + replacement.rstrip() + "\n" + src[end:]
        i += 1
    raise RuntimeError(f"closing brace not found: {signature_prefix}")


helper = r'''
// CGEMU342 native multi-ROM support for Android NES.emu.
// Supported container names: multirom1.nes ... multirom4.nes
// Container footer/directory layout matches coolgirl-combiner-emu.
namespace
{
struct CgemuEntry
{
    uint64_t offset{};
    uint64_t size{};
    uint16_t format{};
    std::string title;
};

MapIO cgemuContainer;
std::vector<CgemuEntry> cgemuEntries;
bool cgemuMenuActive{};
bool cgemuLaunchGuard{};

uint16_t cgRead16(const uint8_t *p)
{
    return uint16_t(p[0]) | (uint16_t(p[1]) << 8);
}

uint32_t cgRead32(const uint8_t *p)
{
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) |
        (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}

uint64_t cgRead64(const uint8_t *p)
{
    return uint64_t(cgRead32(p)) | (uint64_t(cgRead32(p + 4)) << 32);
}

bool cgSupportedName(std::string_view name)
{
    auto slash = name.find_last_of("/\\");
    if(slash != std::string_view::npos)
        name.remove_prefix(slash + 1);
    return name == "multirom1.nes" || name == "multirom2.nes" ||
        name == "multirom3.nes" || name == "multirom4.nes";
}

std::string cgReadTitle(const uint8_t *p)
{
    size_t len = 0;
    while(len < 128 && p[len])
        ++len;
    return std::string{reinterpret_cast<const char*>(p), len};
}

bool cgSetupContainer(IO &io, std::string_view name)
{
    cgemuContainer = {};
    cgemuEntries.clear();
    cgemuMenuActive = false;
    cgemuLaunchGuard = false;

    if(!cgSupportedName(name))
        return false;

    MapIO candidate{io};
    if(!candidate || candidate.size() < 48)
        return false;

    const auto *data = candidate.data();
    const size_t totalSize = candidate.size();
    const size_t footerPos = totalSize - 48;
    const uint8_t magic[8] = {'C','G','E','M','U','3','4','2'};
    for(size_t i = 0; i < 8; ++i)
        if(data[footerPos + i] != magic[i])
            return false;

    const uint32_t version = cgRead32(data + footerPos + 8);
    const uint32_t count = cgRead32(data + footerPos + 12);
    const uint64_t dirOffset = cgRead64(data + footerPos + 16);
    const uint64_t dirSize = cgRead64(data + footerPos + 24);

    if(version != 1 || count == 0 || count > 65535)
        return false;
    if(dirOffset > footerPos || dirSize > uint64_t(footerPos) - dirOffset)
        return false;
    if(dirSize < uint64_t(count) * 288ULL)
        return false;

    cgemuEntries.reserve(count);
    for(uint32_t i = 0; i < count; ++i)
    {
        const uint64_t entryPos64 = dirOffset + uint64_t(i) * 288ULL;
        if(entryPos64 > footerPos || 288ULL > uint64_t(footerPos) - entryPos64)
            return false;
        const auto *entry = data + size_t(entryPos64);
        const uint64_t offset = cgRead64(entry + 0);
        const uint64_t size = cgRead64(entry + 8);
        const uint16_t format = cgRead16(entry + 16);
        if(offset > dirOffset || size > dirOffset - offset)
            return false;
        cgemuEntries.push_back({offset, size, format, cgReadTitle(entry + 24)});
    }

    cgemuContainer = std::move(candidate);
    cgemuMenuActive = true;
    NesSystem::log.info("CGEMU342 Android container active: {} games", cgemuEntries.size());
    return true;
}

bool cgLaunchSelected(NesSystem &sys, unsigned id)
{
    if(!cgemuMenuActive || id >= cgemuEntries.size())
    {
        NesSystem::log.error("CGEMU342 invalid game id:{} count:{}", id, cgemuEntries.size());
        return false;
    }

    const auto &entry = cgemuEntries[id];
    if(entry.offset > cgemuContainer.size() || entry.size > uint64_t(cgemuContainer.size()) - entry.offset)
        return false;

    MapIO gameView = cgemuContainer.subView((off_t)entry.offset, (size_t)entry.size);
    auto ioStream = new EmuFileIO(std::move(gameView));
    auto file = new FCEUFILE();

    std::string logicalName = entry.title.empty() ? std::string{"CGEMU342"} : entry.title;
    logicalName += entry.format == 3 ? ".unf" : ".nes";
    file->filename = logicalName;
    file->archiveIndex = -1;
    file->stream = ioStream;
    file->size = ioStream->size();

    FCEUI_CloseGame();
    if(!FCEUI_LoadGameWithFileVirtual(file, logicalName.c_str(), 0, false))
    {
        NesSystem::log.error("CGEMU342 failed to load id:{}", id);
        cgemuMenuActive = false;
        return false;
    }

    sys.autoDetectedRegion = regionFromName(logicalName);
    setRegion(sys.optionVideoSystem, sys.optionDefaultVideoSystem, sys.autoDetectedRegion);
    sys.setupNESInputPorts();
    EMUFILE_MEMORY stateMemFile;
    FCEUSS_SaveMS(&stateMemFile, 0);
    sys.saveStateSize = stateMemFile.get_vec()->size();
    cgemuMenuActive = false;
    NesSystem::log.info("CGEMU342 launched id:{} {}", id, logicalName);
    return true;
}
}
'''

load_replacement = helper + r'''
void NesSystem::loadContent(IO &io, EmuSystemCreateParams, OnLoadProgressDelegate)
{
    cgSetupContainer(io, contentFileName());

    auto ioStream = new EmuFileIO(io);
    auto file = new FCEUFILE();
    file->filename = contentFileName();
    file->archiveIndex = -1;
    file->stream = ioStream;
    file->size = ioStream->size();
    if(auto ipsFile = FileUtils::fopenUri(appContext(), userFilePath(patchesDir, ".ips"), "r");
        ipsFile)
    {
        ApplyIPS(ipsFile, file);
    }
    if(!FCEUI_LoadGameWithFileVirtual(file, contentFileName().data(), 0, false))
    {
        cgemuMenuActive = false;
        if(loaderErrorString.size())
            throw std::runtime_error(std::exchange(loaderErrorString, {}));
        else
            throw std::runtime_error("Error loading game");
    }
    autoDetectedRegion = regionFromName(contentFileName());
    setRegion(optionVideoSystem, optionDefaultVideoSystem, autoDetectedRegion);
    setupNESInputPorts();
    EMUFILE_MEMORY stateMemFile;
    FCEUSS_SaveMS(&stateMemFile, 0);
    saveStateSize = stateMemFile.get_vec()->size();
}
'''

run_replacement = r'''
void NesSystem::runFrame(EmuSystemTaskContext taskCtx, EmuVideo *video, EmuAudio *audio)
{
    bool skip = !video && !optionCompatibleFrameskip;
    FCEUI_Emulate(taskCtx, static_cast<NesSystemHolder&>(*this), video, skip, audio);

    if(!cgemuMenuActive)
        return;

    const uint8_t magic = X6502_DMR(0x07F2);
    if(magic == 0xA5 && !cgemuLaunchGuard)
    {
        cgemuLaunchGuard = true;
        const unsigned id = unsigned(X6502_DMR(0x07F0)) |
            (unsigned(X6502_DMR(0x07F1)) << 8);
        X6502_DMW(0x07F2, 0);
        cgLaunchSelected(*this, id);
    }
    else if(magic != 0xA5)
    {
        cgemuLaunchGuard = false;
    }
}
'''

if "CGEMU342 native multi-ROM support for Android NES.emu" not in text:
    text = replace_function(text, "void NesSystem::loadContent(IO &io", load_replacement)
else:
    raise RuntimeError("CGEMU342 patch already present")

text = replace_function(text, "void NesSystem::runFrame(EmuSystemTaskContext taskCtx", run_replacement)
MAIN.write_text(text, encoding="utf-8")
print(f"patched {MAIN}")
