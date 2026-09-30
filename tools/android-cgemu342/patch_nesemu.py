#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[2] / "emu-ex-plus-alpha"
system = root / "NES.emu/src/main/system.ccm"
main = root / "NES.emu/src/main/Main.cc"

s = system.read_text()
anchor = "\tstd::string loaderErrorString;\n"
insert = r'''\tstd::string loaderErrorString;

\tstruct CgEntry
\t{
\t\tuint64_t offset{};
\t\tuint64_t size{};
\t\tuint16_t format{};
\t\tuint16_t mapper{};
\t\tuint16_t submapper{};
\t\tstd::string title;
\t};
\tstd::vector<uint8_t> cgemuContainer;
\tstd::vector<CgEntry> cgemuEntries;
\tbool cgemuActive{};
\tbool cgemuMenuRunning{};
\tbool cgemuLaunchGuard{};
'''.replace('\\t','\t').replace('\\n','\n')
if anchor not in s:
    raise SystemExit("system.ccm anchor not found")
s = s.replace(anchor, insert, 1)
system.write_text(s)

m = main.read_text()
load_start = m.index("void NesSystem::loadContent(IO &io, EmuSystemCreateParams, OnLoadProgressDelegate)\n{")
load_end = m.index("\n}\n\nbool NesSystem::onVideoRenderFormatChange", load_start) + 2
new_load = r'''static uint16_t cgRead16(const uint8_t *p)
{
\treturn uint16_t(p[0]) | (uint16_t(p[1]) << 8);
}

static uint32_t cgRead32(const uint8_t *p)
{
\treturn uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}

static uint64_t cgRead64(const uint8_t *p)
{
\treturn uint64_t(cgRead32(p)) | (uint64_t(cgRead32(p + 4)) << 32);
}

static std::string cgReadText(const uint8_t *p, size_t n)
{
\tsize_t len = 0;
\twhile(len < n && p[len]) ++len;
\treturn std::string{reinterpret_cast<const char*>(p), len};
}

static bool cgIsContainerName(std::string_view n)
{
\treturn n == "multirom1.nes" || n == "multirom2.nes" || n == "multirom3.nes" || n == "multirom4.nes";
}

static void finishLoadedNesGame(NesSystem &sys, std::string_view logicalName)
{
\tsys.autoDetectedRegion = regionFromName(logicalName);
\tsetRegion(sys.optionVideoSystem, sys.optionDefaultVideoSystem, sys.autoDetectedRegion);
\tsys.setupNESInputPorts();
\tEMUFILE_MEMORY stateMemFile;
\tFCEUSS_SaveMS(&stateMemFile, 0);
\tsys.saveStateSize = stateMemFile.get_vec()->size();
}

static bool parseCgContainer(NesSystem &sys)
{
\tsys.cgemuEntries.clear();
\tauto &v = sys.cgemuContainer;
\tif(v.size() < 48) return false;
\tconst uint8_t *f = v.data() + v.size() - 48;
\tif(std::memcmp(f, "CGEMU342", 8) != 0) return false;
\tif(cgRead32(f + 8) != 1) return false;
\tuint32_t count = cgRead32(f + 12);
\tuint64_t dirOff = cgRead64(f + 16);
\tuint64_t dirSize = cgRead64(f + 24);
\tif(!count || dirSize < uint64_t(count) * 288 || dirOff > v.size() - 48 || dirOff + dirSize > v.size() - 48) return false;
\tfor(uint32_t i = 0; i < count; ++i)
\t{
\t\tconst uint8_t *e = v.data() + dirOff + uint64_t(i) * 288;
\t\tNesSystem::CgEntry out;
\t\tout.offset = cgRead64(e);
\t\tout.size = cgRead64(e + 8);
\t\tout.format = cgRead16(e + 16);
\t\tout.mapper = cgRead16(e + 18);
\t\tout.submapper = cgRead16(e + 20);
\t\tout.title = cgReadText(e + 24, 128);
\t\tif(!out.size || out.offset > dirOff || out.size > dirOff - out.offset) return false;
\t\tsys.cgemuEntries.emplace_back(std::move(out));
\t}
\treturn true;
}

static bool loadCgGame(NesSystem &sys, unsigned id)
{
\tif(id >= sys.cgemuEntries.size()) return false;
\tauto &e = sys.cgemuEntries[id];
\tauto mem = new EMUFILE_MEMORY(sys.cgemuContainer.data() + e.offset, e.size);
\tauto file = new FCEUFILE();
\tstd::string logical = e.title.empty() ? std::string{"cgemu_game"} : e.title;
\tlogical += e.format == 3 ? ".unf" : ".nes";
\tfile->filename = logical;
\tfile->archiveIndex = -1;
\tfile->stream = mem;
\tfile->size = e.size;
\tif(!FCEUI_LoadGameWithFileVirtual(file, logical.c_str(), 0, false)) return false;
\tfinishLoadedNesGame(sys, logical);
\tsys.cgemuMenuRunning = false;
\treturn true;
}

void NesSystem::loadContent(IO &io, EmuSystemCreateParams, OnLoadProgressDelegate)
{
\tcgemuActive = false;
\tcgemuMenuRunning = false;
\tcgemuLaunchGuard = false;
\tcgemuContainer.clear();
\tcgemuEntries.clear();

\tFCEUFILE *file = new FCEUFILE();
\tif(cgIsContainerName(contentFileName()))
\t{
\t\tauto sz = io.size();
\t\tcgemuContainer.resize(sz);
\t\tif(sz && io.read(cgemuContainer.data(), sz) == (ssize_t)sz && parseCgContainer(*this))
\t\t{
\t\t\tcgemuActive = true;
\t\t\tcgemuMenuRunning = true;
\t\t\tfile->stream = new EMUFILE_MEMORY(&cgemuContainer);
\t\t\tfile->size = cgemuContainer.size();
\t\t}
\t\telse
\t\t{
\t\t\tdelete file;
\t\t\tthrow std::runtime_error("Invalid CGEMU342 multirom container");
\t\t}
\t}
\telse
\t{
\t\tauto ioStream = new EmuFileIO(io);
\t\tfile->stream = ioStream;
\t\tfile->size = ioStream->size();
\t}
\tfile->filename = contentFileName();
\tfile->archiveIndex = -1;
\tif(auto ipsFile = FileUtils::fopenUri(appContext(), userFilePath(patchesDir, ".ips"), "r"); ipsFile)
\t{
\t\tApplyIPS(ipsFile, file);
\t}
\tif(!FCEUI_LoadGameWithFileVirtual(file, contentFileName().data(), 0, false))
\t{
\t\tif(loaderErrorString.size()) throw std::runtime_error(std::exchange(loaderErrorString, {}));
\t\tthrow std::runtime_error("Error loading game");
\t}
\tfinishLoadedNesGame(*this, contentFileName());
}
'''.replace('\\t','\t').replace('\\n','\n')
m = m[:load_start] + new_load + m[load_end:]
old_run = '''void NesSystem::runFrame(EmuSystemTaskContext taskCtx, EmuVideo *video, EmuAudio *audio)\n{\n\tbool skip = !video && !optionCompatibleFrameskip;\n\tFCEUI_Emulate(taskCtx, static_cast<NesSystemHolder&>(*this), video, skip, audio);\n}'''
new_run = '''void NesSystem::runFrame(EmuSystemTaskContext taskCtx, EmuVideo *video, EmuAudio *audio)\n{\n\tbool skip = !video && !optionCompatibleFrameskip;\n\tFCEUI_Emulate(taskCtx, static_cast<NesSystemHolder&>(*this), video, skip, audio);\n\tif(cgemuActive && cgemuMenuRunning && RAM)\n\t{\n\t\tauto magic = RAM[0x07F2];\n\t\tif(magic == 0xA5 && !cgemuLaunchGuard)\n\t\t{\n\t\t\tcgemuLaunchGuard = true;\n\t\t\tunsigned id = unsigned(RAM[0x07F0]) | (unsigned(RAM[0x07F1]) << 8);\n\t\t\tRAM[0x07F2] = 0;\n\t\t\tloadCgGame(*this, id);\n\t\t}\n\t\telse if(magic != 0xA5)\n\t\t{\n\t\t\tcgemuLaunchGuard = false;\n\t\t}\n\t}\n}'''
if old_run not in m:
    raise SystemExit("runFrame anchor not found")
m = m.replace(old_run, new_run, 1)
main.write_text(m)
print("Patched NES.emu for native CGEMU342 multirom1..4 support")
