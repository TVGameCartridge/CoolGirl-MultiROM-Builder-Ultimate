from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
p = root / "Core/NES/Mappers/Unlicensed/CoolGirl342.h"
s = p.read_text(encoding="utf-8-sig").replace("\r\n", "\n")

def once(old, new, label):
    global s
    if old in s:
        s = s.replace(old, new, 1)
    elif new not in s:
        raise SystemExit("CGEMU342 native launcher patch marker missing: " + label)

once(
    '#include "NES/NesCpu.h"\n',
    '#include "NES/NesCpu.h"\n#include "NES/NesMemoryManager.h"\n'
    '#include <fstream>\n#include <filesystem>\n#ifdef _WIN32\n#include <windows.h>\n#endif\n',
    "includes",
)
once(
    "\tuint64_t _a12LowClock = 0;\n",
    "\tuint64_t _a12LowClock = 0;\n\tbool _cgemuLaunchInProgress = false;\n",
    "state",
)

launcher = r'''
\tstatic uint16_t ReadU16(const uint8_t* p)
\t{
\t\treturn (uint16_t)p[0] | ((uint16_t)p[1] << 8);
\t}

\tstatic uint32_t ReadU32(const uint8_t* p)
\t{
\t\treturn (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
\t}

\tstatic uint64_t ReadU64(const uint8_t* p)
\t{
\t\treturn (uint64_t)ReadU32(p) | ((uint64_t)ReadU32(p + 4) << 32);
\t}

\tstatic void RestoreNesMapperHeader(vector<uint8_t>& data, uint16_t mapper, uint16_t submapper)
\t{
\t\tif(data.size() < 16 || data[0] != 'N' || data[1] != 'E' || data[2] != 'S' || data[3] != 0x1A) {
\t\t\treturn;
\t\t}
\t\tbool wasNes2 = (data[7] & 0x0C) == 0x08;
\t\tdata[6] = (data[6] & 0x0F) | ((mapper & 0x0F) << 4);
\t\tbool needNes2 = mapper >= 256 || submapper != 0;
\t\tif(needNes2) {
\t\t\tdata[7] = (data[7] & 0x03) | 0x08 | (((mapper >> 4) & 0x0F) << 4);
\t\t\tdata[8] = ((submapper & 0x0F) << 4) | ((mapper >> 8) & 0x0F);
\t\t} else {
\t\t\tdata[7] = (data[7] & 0x0F) | (((mapper >> 4) & 0x0F) << 4);
\t\t\tif(wasNes2) {
\t\t\t\tdata[8] = 0;
\t\t\t}
\t\t}
\t}

\tbool LaunchEmbeddedGame(uint16_t gameId)
\t{
#ifdef _WIN32
\t\ttry {
\t\t\tstd::filesystem::path sourcePath = std::filesystem::u8path(_romInfo.Filename);
\t\t\tstd::ifstream src(sourcePath, std::ios::binary);
\t\t\tif(!src) return false;

\t\t\tsrc.seekg(0, std::ios::end);
\t\t\tuint64_t fileSize = (uint64_t)src.tellg();
\t\t\tif(fileSize < 48) return false;

\t\t\tuint8_t footer[48] = {};
\t\t\tsrc.seekg((std::streamoff)(fileSize - 48), std::ios::beg);
\t\t\tsrc.read((char*)footer, sizeof(footer));
\t\t\tif(src.gcount() != sizeof(footer) || memcmp(footer, "CGEMU342", 8) != 0) return false;

\t\t\tuint32_t version = ReadU32(footer + 8);
\t\t\tuint32_t count = ReadU32(footer + 12);
\t\t\tuint64_t dirOffset = ReadU64(footer + 16);
\t\t\tuint64_t dirSize = ReadU64(footer + 24);
\t\t\tif(version != 1 || gameId >= count || dirSize < (uint64_t)count * 288ULL ||
\t\t\t\tdirOffset + dirSize > fileSize - 48) return false;

\t\t\tuint8_t entry[288] = {};
\t\t\tsrc.seekg((std::streamoff)(dirOffset + (uint64_t)gameId * 288ULL), std::ios::beg);
\t\t\tsrc.read((char*)entry, sizeof(entry));
\t\t\tif(src.gcount() != sizeof(entry)) return false;

\t\t\tuint64_t payloadOffset = ReadU64(entry + 0);
\t\t\tuint64_t payloadSize = ReadU64(entry + 8);
\t\t\tuint16_t format = ReadU16(entry + 16);
\t\t\tuint16_t mapper = ReadU16(entry + 18);
\t\t\tuint16_t submapper = ReadU16(entry + 20);
\t\t\tif(payloadSize == 0 || payloadOffset > fileSize || payloadSize > fileSize - payloadOffset ||
\t\t\t\tpayloadSize > (uint64_t)SIZE_MAX) return false;

\t\t\tvector<uint8_t> payload((size_t)payloadSize);
\t\t\tsrc.seekg((std::streamoff)payloadOffset, std::ios::beg);
\t\t\tsrc.read((char*)payload.data(), (std::streamsize)payload.size());
\t\t\tif((size_t)src.gcount() != payload.size()) return false;

\t\t\tstd::wstring ext = format == 3 ? L".unf" : L".nes";
\t\t\tif(format != 3) RestoreNesMapperHeader(payload, mapper, submapper);

\t\t\tstd::wstring name = L".cgemu342_game_" + std::to_wstring(gameId)
\t\t\t\t+ L"_m" + std::to_wstring(mapper);
\t\t\tif(submapper) name += L"s" + std::to_wstring(submapper);
\t\t\tname += ext;
\t\t\tstd::filesystem::path outputPath = sourcePath.parent_path() / name;

\t\t\tstd::ofstream dst(outputPath, std::ios::binary | std::ios::trunc);
\t\t\tif(!dst) return false;
\t\t\tdst.write((const char*)payload.data(), (std::streamsize)payload.size());
\t\t\tdst.close();
\t\t\tif(!dst) return false;

\t\t\twchar_t exePath[32768] = {};
\t\t\tDWORD exeLen = GetModuleFileNameW(nullptr, exePath, (DWORD)(sizeof(exePath) / sizeof(exePath[0])));
\t\t\tif(exeLen == 0 || exeLen >= (DWORD)(sizeof(exePath) / sizeof(exePath[0]))) return false;

\t\t\tstd::wstring command = L"\"" + std::wstring(exePath) + L"\" \"" + outputPath.wstring() + L"\"";
\t\t\tvector<wchar_t> cmd(command.begin(), command.end());
\t\t\tcmd.push_back(L'\0');

\t\t\tSTARTUPINFOW si = {};
\t\t\tPROCESS_INFORMATION pi = {};
\t\t\tsi.cb = sizeof(si);
\t\t\tstd::wstring workDir = sourcePath.parent_path().wstring();
\t\t\tBOOL ok = CreateProcessW(exePath, cmd.data(), nullptr, nullptr, FALSE, 0,
\t\t\t\tnullptr, workDir.empty() ? nullptr : workDir.c_str(), &si, &pi);
\t\t\tif(ok) {
\t\t\t\tCloseHandle(pi.hThread);
\t\t\t\tCloseHandle(pi.hProcess);
\t\t\t\treturn true;
\t\t\t}
\t\t} catch(...) {
\t\t\treturn false;
\t\t}
#endif
\t\treturn false;
\t}
'''.replace('\\t','\t')
marker = "\tbool IsA12RisingEdge(uint16_t addr)\n\t{"
if launcher not in s:
    if marker not in s:
        raise SystemExit("CGEMU342 native launcher patch marker missing: launcher insertion")
    s = s.replace(marker, launcher + "\n" + marker, 1)

once(
    "\tbool EnableVramAddressHook() override { return true; }\n",
    "\tbool EnableVramAddressHook() override { return true; }\n\tbool EnableCpuClockHook() override { return true; }\n",
    "cpu clock enable",
)
once(
    "\t\t_a12LowClock = 0;\n\t}\n\nprotected:",
    "\t\t_a12LowClock = 0;\n\t\t_cgemuLaunchInProgress = false;\n\t}\n\nprotected:",
    "reset launcher state",
)

process_clock = r'''
\tvoid ProcessCpuClock() override
\t{
\t\tBaseProcessCpuClock();
\t\tuint8_t* ram = _console->GetMemoryManager()->GetInternalRam();
\t\tif(!_cgemuLaunchInProgress && ram && ram[0x7F2] == 0xA5) {
\t\t\tuint16_t gameId = (uint16_t)ram[0x7F0] | ((uint16_t)ram[0x7F1] << 8);
\t\t\tram[0x7F2] = 0;
\t\t\t_cgemuLaunchInProgress = true;
\t\t\tif(!LaunchEmbeddedGame(gameId)) {
\t\t\t\t_cgemuLaunchInProgress = false;
\t\t\t}
\t\t}
\t}
'''.replace('\\t','\t')
marker = "\tvoid WriteRegister(uint16_t addr, uint8_t value) override\n\t{"
if process_clock not in s:
    if marker not in s:
        raise SystemExit("CGEMU342 native launcher patch marker missing: ProcessCpuClock")
    s = s.replace(marker, process_clock + "\n" + marker, 1)

p.write_text(s, encoding="utf-8", newline="\n")
print("CGEMU342 native standalone-ROM launcher embedded in CoolGirl342")
