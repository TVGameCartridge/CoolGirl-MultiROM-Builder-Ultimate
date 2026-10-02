from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
p = root / "Core/NES/Mappers/JyCompany/JyCompany.h"
s = p.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def once(old, new, label):
    global s
    if old in s:
        s = s.replace(old, new, 1)
    elif new not in s:
        raise SystemExit("mapper358 patch marker missing: " + label)


once(
    "\tuint8_t _regRamValue = 0;\n\n\tuint16_t _lastPpuAddr = 0;",
    "\tuint8_t _regRamValue = 0;\n\tuint8_t _mapper358Outer = 0;\n\n\tuint16_t _lastPpuAddr = 0;",
    "state",
)
once(
    "\t\t_regRamValue = 0;\n\n\t\tUpdateState();",
    "\t\t_regRamValue = 0;\n\t\t_mapper358Outer = 0;\n\n\t\tUpdateState();",
    "reset",
)
once(
    "\t\tSV(_regRamValue);\n\n\t\tif(!s.IsSaving()) {",
    "\t\tSV(_regRamValue);\n\t\tSV(_mapper358Outer);\n\n\t\tif(!s.IsSaving()) {",
    "serialize",
)

old = "\tvoid UpdatePrgState()\n\t{\n\t\tbool invertBits = (_prgMode & 0x03) == 0x03;"
new = r'''\tvoid UpdatePrgState()
\t{
\t\tbool invertBits = (_prgMode & 0x03) == 0x03;

\t\tif(_romInfo.MapperID == 358) {
\t\t\t// FCEUmm sync358(): PRG AND=0x1F, OR=(D003<<4)&~0x1F.
\t\t\tuint16_t outer = (uint16_t)(_mapper358Outer << 4) & 0x7E0;
\t\t\tuint8_t p0 = InvertPrgBits(_prgRegs[0], invertBits);
\t\t\tuint8_t p1 = InvertPrgBits(_prgRegs[1], invertBits);
\t\t\tuint8_t p2 = InvertPrgBits(_prgRegs[2], invertBits);
\t\t\tuint8_t p3 = InvertPrgBits(_prgRegs[3], invertBits);
\t\t\tuint8_t last = (_prgMode & 0x04) ? p3 : 0xFF;

\t\t\tswitch(_prgMode & 0x03) {
\t\t\t\tcase 0: {
\t\t\t\t\tuint16_t page = (uint16_t)((((last & 0x1F) >> 2) | (outer >> 2)) << 2);
\t\t\t\t\tSelectPrgPage4x(0, page);
\t\t\t\t\tif(_enablePrgAt6000) SetCpuMemoryMapping(0x6000, 0x7FFF, (int16_t)((((p3 << 2) | 3) & 0x1F) | outer), PrgMemoryType::PrgRom);
\t\t\t\t\tbreak;
\t\t\t\t}
\t\t\t\tcase 1: {
\t\t\t\t\tuint16_t a = (uint16_t)((((p1 & 0x1F) >> 1) | (outer >> 1)) << 1);
\t\t\t\t\tuint16_t b = (uint16_t)((((last & 0x1F) >> 1) | (outer >> 1)) << 1);
\t\t\t\t\tSelectPrgPage2x(0, a);
\t\t\t\t\tSelectPrgPage2x(1, b);
\t\t\t\t\tif(_enablePrgAt6000) SetCpuMemoryMapping(0x6000, 0x7FFF, (int16_t)((((p3 << 1) | 1) & 0x1F) | outer), PrgMemoryType::PrgRom);
\t\t\t\t\tbreak;
\t\t\t\t}
\t\t\t\tcase 2:
\t\t\t\tcase 3:
\t\t\t\t\tSelectPrgPage(0, (p0 & 0x1F) | outer);
\t\t\t\t\tSelectPrgPage(1, (p1 & 0x1F) | outer);
\t\t\t\t\tSelectPrgPage(2, (p2 & 0x1F) | outer);
\t\t\t\t\tSelectPrgPage(3, (last & 0x1F) | outer);
\t\t\t\t\tif(_enablePrgAt6000) SetCpuMemoryMapping(0x6000, 0x7FFF, (int16_t)((p3 & 0x1F) | outer), PrgMemoryType::PrgRom);
\t\t\t\t\tbreak;
\t\t\t}
\t\t\tif(!_enablePrgAt6000) RemoveCpuMemoryMapping(0x6000, 0x7FFF);
\t\t\treturn;
\t\t}
'''.replace('\\t', '\t')
once(old, new, "PRG")

old = "\tuint16_t GetChrReg(int index)\n\t{\n\t\tif(_chrMode >= 2 && _mirrorChr && (index == 2 || index == 3)) {\n\t\t\tindex -= 2;\n\t\t}"
new = r'''\tuint16_t GetChrReg(int index)
\t{
\t\tif(_chrMode >= 2 && _mirrorChr && (index == 2 || index == 3)) {
\t\t\tindex -= 2;
\t\t}

\t\tif(_romInfo.MapperID == 358) {
\t\t\tuint16_t raw = _chrLowRegs[index] | ((uint16_t)_chrHighRegs[index] << 8);
\t\t\tuint16_t andMask, orMask;
\t\t\tif(_mapper358Outer & 0x20) {
\t\t\t\tandMask = 0x1FF;
\t\t\t\torMask = ((uint16_t)_mapper358Outer << 7) & 0x600;
\t\t\t} else {
\t\t\t\tandMask = 0x0FF;
\t\t\t\torMask = (((uint16_t)_mapper358Outer << 8) & 0x100) | (((uint16_t)_mapper358Outer << 7) & 0x600);
\t\t\t}
\t\t\tuint8_t shift = 3 - (_chrMode & 3);
\t\t\treturn (uint16_t)((raw & (andMask >> shift)) | (orMask >> shift));
\t\t}
'''.replace('\\t', '\t')
once(old, new, "CHR")

once(
    "\t\t\t\tcase 0xD003:\n\t\t\t\t\t_mirrorChr = (value & 0x80) == 0x80;",
    "\t\t\t\tcase 0xD003:\n\t\t\t\t\t_mapper358Outer = value;\n\t\t\t\t\t_mirrorChr = (value & 0x80) == 0x80;",
    "D003",
)

once(
    "\t\t\t\t\tuint16_t chrPage = _ntLowRegs[ntIndex] | (_ntHighRegs[ntIndex] << 8);\n\t\t\t\t\tuint32_t chrOffset = chrPage * 0x400 + (addr & 0x3FF);",
    "\t\t\t\t\tuint16_t chrPage = _ntLowRegs[ntIndex] | (_ntHighRegs[ntIndex] << 8);\n"
    "\t\t\t\t\tif(_romInfo.MapperID == 358) {\n"
    "\t\t\t\t\t\tuint16_t andMask, orMask;\n"
    "\t\t\t\t\t\tif(_mapper358Outer & 0x20) { andMask = 0x1FF; orMask = ((uint16_t)_mapper358Outer << 7) & 0x600; }\n"
    "\t\t\t\t\t\telse { andMask = 0x0FF; orMask = (((uint16_t)_mapper358Outer << 8) & 0x100) | (((uint16_t)_mapper358Outer << 7) & 0x600); }\n"
    "\t\t\t\t\t\tchrPage = (chrPage & andMask) | orMask;\n"
    "\t\t\t\t\t}\n"
    "\t\t\t\t\tuint32_t chrOffset = chrPage * 0x400 + (addr & 0x3FF);",
    "nametable",
)

once(
    "\t\tif(_romInfo.MapperID == 209) {\n\t\t\tswitch(addr & 0x2FF8) {",
    "\t\tif(_romInfo.MapperID == 209 || (_romInfo.MapperID == 358 && (_mapper358Outer & 0x80) && _chrMode == 1)) {\n\t\t\tswitch(addr & 0x2FF8) {",
    "MMC4 latch",
)

p.write_text(s, encoding="utf-8", newline="\n")
print("mapper 358 exact JY multicart wiring patched")
