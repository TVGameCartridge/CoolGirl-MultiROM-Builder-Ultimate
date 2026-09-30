from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
main = root / "NES.emu" / "src" / "main" / "Main.cc"
text = main.read_text(encoding="utf-8")

# Need direct, side-effect-free NES RAM reads, and a memory-backed FCEUFILE for
# launching a selected ROM directly from the appended CGEMU342 container.
needle = '#include <fceu/debug.h>'
if needle not in text:
    text = text.replace('#include <fceu/state.h>\n', '#include <fceu/state.h>\n#include <fceu/debug.h>\n#include <fceu/emufile.h>\n', 1)

helper = r'''

// ---------------------------------------------------------------------------
// CGEMU342 embedded multi-ROM support
//
// Layout at EOF:
//   "CGEMU342" + version(u32) + count(u32) + dirOff(u64) + dirSize(u64)
//   + payloadStart(u64) + reserved(u64)
// Directory entries are 288 bytes and contain payload offset/size plus the
// original file format. The menu asks for a game via ordinary NES RAM:
//   $07F0/$07F1 = zero-based game id, $07F2 = $A5 launch request.
//
// The original container is retained in memory while a child game is running.
// This avoids Android content:// path and storage-permission problems entirely.
// ---------------------------------------------------------------------------
static std::vector<uint8_t> cgemu342Container;
static bool cgemu342ContainerValid = false;
static bool cgemu342ChildActive = false;
static bool cgemu342LaunchGuard = false;

static uint16_t cgemu342Rd16(const uint8_t *p)
{
    return uint16_t(p[0]) | (uint16_t(p[1]) << 8);
}

static uint32_t cgemu342Rd32(const uint8_t *p)
{
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) |
        (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}

static uint64_t cgemu342Rd64(const uint8_t *p)
{
    return uint64_t(cgemu342Rd32(p)) | (uint64_t(cgemu342Rd32(p + 4)) << 32);
}

static bool cgemu342Footer(std::span<const uint8_t> data,
    uint32_t &count, uint64_t &dirOff, uint64_t &dirSize)
{
    if(data.size() < 48)
        return false;
    const auto *f = data.data() + data.size() - 48;
    if(std::memcmp(f, "CGEMU342", 8) != 0 || cgemu342Rd32(f + 8) != 1)
        return false;
    count = cgemu342Rd32(f + 12);
    dirOff = cgemu342Rd64(f + 16);
    dirSize = cgemu342Rd64(f + 24);
    if(!count || dirSize < uint64_t(count) * 288ULL)
        return false;
    const uint64_t footerOff = data.size() - 48;
    return dirOff <= footerOff && dirSize <= footerOff - dirOff;
}

static bool cgemu342LoadBytes(const uint8_t *bytes, size_t size, const char *logicalName)
{
    auto stream = new EMUFILE_MEMORY((void*)bytes, size);
    auto file = new FCEUFILE();
    file->filename = logicalName;
    file->archiveIndex = -1;
    file->stream = stream;
    file->size = stream->size();
    return FCEUI_LoadGameWithFileVirtual(file, logicalName, 0, false) != nullptr;
}

static bool cgemu342LaunchGame(unsigned id)
{
    if(!cgemu342ContainerValid)
        return false;

    uint32_t count = 0;
    uint64_t dirOff = 0, dirSize = 0;
    std::span<const uint8_t> all{cgemu342Container.data(), cgemu342Container.size()};
    if(!cgemu342Footer(all, count, dirOff, dirSize) || id >= count)
        return false;

    const uint64_t ep = dirOff + uint64_t(id) * 288ULL;
    if(ep + 288 > all.size())
        return false;
    const uint8_t *e = all.data() + ep;
    const uint64_t off = cgemu342Rd64(e + 0);
    const uint64_t len = cgemu342Rd64(e + 8);
    const uint16_t fmt = cgemu342Rd16(e + 16);
    if(!len || off > all.size() || len > all.size() - off)
        return false;

    char name[64];
    std::snprintf(name, sizeof(name), "CGEMU342_%03u.%s", id, fmt == 3 ? "unf" : "nes");
    return cgemu342LoadBytes(all.data() + off, size_t(len), name);
}

static bool cgemu342ReturnToMenu()
{
    if(!cgemu342ContainerValid || cgemu342Container.empty())
        return false;
    return cgemu342LoadBytes(cgemu342Container.data(), cgemu342Container.size(), "multirom.nes");
}
'''

ns = 'namespace EmuEx\n{\n'
if 'static std::vector<uint8_t> cgemu342Container;' not in text:
    if ns not in text:
        raise SystemExit('namespace insertion point not found')
    text = text.replace(ns, ns + helper, 1)

old_reset = '''void NesSystem::reset(EmuApp &app, ResetMode mode)\n{\n\tassume(hasContent());\n\tif(mode == ResetMode::HARD)\n\t\tFCEUI_PowerNES();\n\telse\n\t\tFCEUI_ResetNES();\n}\n'''
new_reset = '''void NesSystem::reset(EmuApp &app, ResetMode mode)\n{\n\tassume(hasContent());\n\t// In an extracted CGEMU342 game, Hard Reset returns to the multi-ROM menu.\n\tif(mode == ResetMode::HARD && cgemu342ChildActive && cgemu342ReturnToMenu())\n\t{\n\t\tcgemu342ChildActive = false;\n\t\tcgemu342LaunchGuard = false;\n\t\tsetupNESInputPorts();\n\t\treturn;\n\t}\n\tif(mode == ResetMode::HARD)\n\t\tFCEUI_PowerNES();\n\telse\n\t\tFCEUI_ResetNES();\n}\n'''
if old_reset in text:
    text = text.replace(old_reset, new_reset, 1)
elif 'cgemu342ReturnToMenu()' not in text[text.find('void NesSystem::reset'):text.find('void NesSystem::reset')+700]:
    raise SystemExit('reset function pattern not found')

old_close = '''void NesSystem::closeSystem()\n{\n\tFCEUI_CloseGame();\n\tfdsIsAccessing = false;\n}\n'''
new_close = '''void NesSystem::closeSystem()\n{\n\tFCEUI_CloseGame();\n\tfdsIsAccessing = false;\n\tcgemu342Container.clear();\n\tcgemu342Container.shrink_to_fit();\n\tcgemu342ContainerValid = false;\n\tcgemu342ChildActive = false;\n\tcgemu342LaunchGuard = false;\n}\n'''
if old_close in text:
    text = text.replace(old_close, new_close, 1)
elif 'cgemu342Container.clear()' not in text:
    raise SystemExit('closeSystem pattern not found')

load_start = '''void NesSystem::loadContent(IO &io, EmuSystemCreateParams, OnLoadProgressDelegate)\n{\n\tauto ioStream = new EmuFileIO(io);\n'''
load_repl = '''void NesSystem::loadContent(IO &io, EmuSystemCreateParams, OnLoadProgressDelegate)\n{\n\t// Retain a CGEMU342 container so selected games can be re-opened directly\n\t// from memory even when Android supplied the ROM through a content:// URI.\n\tcgemu342Container.clear();\n\tcgemu342ContainerValid = false;\n\tcgemu342ChildActive = false;\n\tcgemu342LaunchGuard = false;\n\tif(auto mapped = io.buffer(); mapped && mapped.size() >= 48)\n\t{\n\t\tuint32_t count = 0; uint64_t dirOff = 0, dirSize = 0;\n\t\tstd::span<const uint8_t> view{mapped.data(), mapped.size()};\n\t\tif(cgemu342Footer(view, count, dirOff, dirSize))\n\t\t{\n\t\t\tcgemu342Container.assign(view.begin(), view.end());\n\t\t\tcgemu342ContainerValid = true;\n\t\t\tlog.info("CGEMU342 container detected: {} games", count);\n\t\t}\n\t}\n\tauto ioStream = new EmuFileIO(io);\n'''
if load_start in text:
    text = text.replace(load_start, load_repl, 1)
elif 'CGEMU342 container detected' not in text:
    raise SystemExit('loadContent insertion point not found')

old_run = '''void NesSystem::runFrame(EmuSystemTaskContext taskCtx, EmuVideo *video, EmuAudio *audio)\n{\n\tbool skip = !video && !optionCompatibleFrameskip;\n\tFCEUI_Emulate(taskCtx, static_cast<NesSystemHolder&>(*this), video, skip, audio);\n}\n'''
new_run = '''void NesSystem::runFrame(EmuSystemTaskContext taskCtx, EmuVideo *video, EmuAudio *audio)\n{\n\tbool skip = !video && !optionCompatibleFrameskip;\n\tFCEUI_Emulate(taskCtx, static_cast<NesSystemHolder&>(*this), video, skip, audio);\n\n\t// Equivalent of cgemu342-embedded.lua, but native and Android-safe.\n\t// The menu waits after writing the request, so switching after the frame is\n\t// complete is safe and ensures the next frame belongs to the selected ROM.\n\tif(cgemu342ContainerValid && !cgemu342ChildActive)\n\t{\n\t\tconst uint8 magic = GetMem(0x07F2);\n\t\tif(magic == 0xA5 && !cgemu342LaunchGuard)\n\t\t{\n\t\t\tcgemu342LaunchGuard = true;\n\t\t\tconst unsigned id = unsigned(GetMem(0x07F0)) | (unsigned(GetMem(0x07F1)) << 8);\n\t\t\tBWrite[0x07F2](0x07F2, 0);\n\t\t\tif(cgemu342LaunchGame(id))\n\t\t\t{\n\t\t\t\tcgemu342ChildActive = true;\n\t\t\t\tsetupNESInputPorts();\n\t\t\t\tlog.info("CGEMU342 launched game id:{}", id);\n\t\t\t}\n\t\t\tcgemu342LaunchGuard = false;\n\t\t}\n\t\telse if(magic != 0xA5)\n\t\t{\n\t\t\tcgemu342LaunchGuard = false;\n\t\t}\n\t}\n}\n'''
if old_run in text:
    text = text.replace(old_run, new_run, 1)
elif 'CGEMU342 launched game id' not in text:
    raise SystemExit('runFrame pattern not found')

main.write_text(text, encoding='utf-8', newline='\n')
print('patched:', main)

# Side-by-side install with the official Play Store NES.emu.
conf = root / 'NES.emu' / 'metadata' / 'conf.mk'
c = conf.read_text(encoding='utf-8')
c = c.replace('metadata_name = NES.emu', 'metadata_name = NES.emu CGEMU342', 1)
c = c.replace('metadata_pkgName = NesEmu', 'metadata_pkgName = NesEmuCG342', 1)
c = c.replace('metadata_id = com.explusalpha.NesEmu', 'metadata_id = com.tvgamecartridge.NesEmuCG342', 1)
conf.write_text(c, encoding='utf-8', newline='\n')
print('patched:', conf)
