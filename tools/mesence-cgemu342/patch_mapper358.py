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

helpers = r'''
\tuint16_t Mapper358PrgPage(uint16_t page)
\t{
\t\tif(_romInfo.MapperID != 358) {
\t\t\treturn page;
\t\t}
\t\tuint16_t base = ((uint16_t)_mapper358Outer << 4) & 0x0FE0;
\t\treturn base | (page & 0x001F);
\t}

\tuint16_t Mapper358ChrPage(uint16_t page)
\t{
\t\tif(_romInfo.MapperID != 358) {
\t\t\treturn page;
\t\t}
\t\tuint16_t base = ((uint16_t)(_mapper358Outer & 0x01) << 8)
\t\t\t| ((uint16_t)(_mapper358Outer & 0x0C) << 7);
\t\tuint16_t mask = 0x00FF;
\t\tif(_mapper358Outer & 0x20) {
\t\t\tbase &= 0x0600;
\t\t\tmask = 0x01FF;
\t\t}
\t\treturn base | (page & mask);
\t}
'''.replace('\\t','\t')
marker = "\tvoid UpdatePrgState()\n\t{"
if helpers not in s:
    if marker not in s:
        raise SystemExit("mapper358 patch marker missing: helpers")
    s = s.replace(marker, helpers + "\n" + marker, 1)

repls = {
    "SelectPrgPage4x(0, (_prgMode & 0x04) ? prgRegs[3] : 0x3C);":
        "SelectPrgPage4x(0, Mapper358PrgPage((_prgMode & 0x04) ? prgRegs[3] : 0x3C));",
    "SetCpuMemoryMapping(0x6000, 0x7FFF, prgRegs[3] * 4 + 3, PrgMemoryType::PrgRom);":
        "SetCpuMemoryMapping(0x6000, 0x7FFF, Mapper358PrgPage(prgRegs[3] * 4 + 3), PrgMemoryType::PrgRom);",
    "SelectPrgPage2x(0, prgRegs[1] << 1);":
        "SelectPrgPage2x(0, Mapper358PrgPage(prgRegs[1] << 1));",
    "SelectPrgPage2x(1, (_prgMode & 0x04) ? prgRegs[3] : 0x3E);":
        "SelectPrgPage2x(1, Mapper358PrgPage((_prgMode & 0x04) ? prgRegs[3] : 0x3E));",
    "SetCpuMemoryMapping(0x6000, 0x7FFF, prgRegs[3] * 2 + 1, PrgMemoryType::PrgRom);":
        "SetCpuMemoryMapping(0x6000, 0x7FFF, Mapper358PrgPage(prgRegs[3] * 2 + 1), PrgMemoryType::PrgRom);",
    "SelectPrgPage(0, prgRegs[0]);":
        "SelectPrgPage(0, Mapper358PrgPage(prgRegs[0]));",
    "SelectPrgPage(1, prgRegs[1]);":
        "SelectPrgPage(1, Mapper358PrgPage(prgRegs[1]));",
    "SelectPrgPage(2, prgRegs[2]);":
        "SelectPrgPage(2, Mapper358PrgPage(prgRegs[2]));",
    "SelectPrgPage(3, (_prgMode & 0x04) ? prgRegs[3] : 0x3F);":
        "SelectPrgPage(3, Mapper358PrgPage((_prgMode & 0x04) ? prgRegs[3] : 0x3F));",
    "SetCpuMemoryMapping(0x6000, 0x7FFF, prgRegs[3], PrgMemoryType::PrgRom);":
        "SetCpuMemoryMapping(0x6000, 0x7FFF, Mapper358PrgPage(prgRegs[3]), PrgMemoryType::PrgRom);",
    "SelectChrPage8x(0, chrRegs[0] << 3);":
        "SelectChrPage8x(0, Mapper358ChrPage(chrRegs[0] << 3));",
    "SelectChrPage4x(0, chrRegs[_chrLatch[0]] << 2);":
        "SelectChrPage4x(0, Mapper358ChrPage(chrRegs[_chrLatch[0]] << 2));",
    "SelectChrPage4x(1, chrRegs[_chrLatch[1]] << 2);":
        "SelectChrPage4x(1, Mapper358ChrPage(chrRegs[_chrLatch[1]] << 2));",
    "SelectChrPage2x(0, chrRegs[0] << 1);":
        "SelectChrPage2x(0, Mapper358ChrPage(chrRegs[0] << 1));",
    "SelectChrPage2x(1, chrRegs[2] << 1);":
        "SelectChrPage2x(1, Mapper358ChrPage(chrRegs[2] << 1));",
    "SelectChrPage2x(2, chrRegs[4] << 1);":
        "SelectChrPage2x(2, Mapper358ChrPage(chrRegs[4] << 1));",
    "SelectChrPage2x(3, chrRegs[6] << 1);":
        "SelectChrPage2x(3, Mapper358ChrPage(chrRegs[6] << 1));",
    "SelectChrPage(i, chrRegs[i]);":
        "SelectChrPage(i, Mapper358ChrPage(chrRegs[i]));",
}
for old,new in repls.items():
    once(old,new,old[:48])

once(
    "\t\t\t\tcase 0xD003:\n\t\t\t\t\t_mirrorChr = (value & 0x80) == 0x80;",
    "\t\t\t\tcase 0xD003:\n\t\t\t\t\tif(_romInfo.MapperID == 358) { _mapper358Outer = value; }\n\t\t\t\t\t_mirrorChr = (value & 0x80) == 0x80;",
    "D003",
)
once(
    "\t\t\t\t\tuint16_t chrPage = _ntLowRegs[ntIndex] | (_ntHighRegs[ntIndex] << 8);\n\t\t\t\t\tuint32_t chrOffset = chrPage * 0x400 + (addr & 0x3FF);",
    "\t\t\t\t\tuint16_t chrPage = _ntLowRegs[ntIndex] | (_ntHighRegs[ntIndex] << 8);\n"
    "\t\t\t\t\tchrPage = Mapper358ChrPage(chrPage);\n"
    "\t\t\t\t\tuint32_t chrOffset = chrPage * 0x400 + (addr & 0x3FF);",
    "nametable",
)
once(
    "\t\tif(_romInfo.MapperID == 209) {",
    "\t\tif(_romInfo.MapperID == 209 || (_romInfo.MapperID == 358 && (_mapper358Outer & 0x80) && _chrMode == 1)) {",
    "MMC4 latch",
)

p.write_text(s, encoding="utf-8", newline="\n")
print("mapper 358 JY outer banking patched in 8K/1K page units")
