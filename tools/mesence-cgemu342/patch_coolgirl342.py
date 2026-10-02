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
        raise SystemExit("CoolGirl342 patch marker missing: " + label)


once(
    "\tbool _mapRomOn6000 = false;\n\tbool _lockout = false;\n\n\tuint8_t _mmc3Sel = 0;",
    "\tbool _mapRomOn6000 = false;\n\tbool _lockout = false;\n\n\tuint8_t _mmc1Load = 0x20;\n\tbool _ppuLatch0 = false;\n\tbool _ppuLatch1 = false;\n\n\tuint8_t _mmc3Sel = 0;",
    "extra state",
)

once(
    "\t\tfor(int i = 0; i < 8; i++) c[i] = MaskChr(_chr[i]);\n\n\t\tswitch(_chrMode & 7) {",
    "\t\tfor(int i = 0; i < 8; i++) c[i] = MaskChr(_chr[i]);\n\n"
    "\t\tif(_mapper == 0x11) { // MMC2/MMC4 PPU latch banks\n"
    "\t\t\tuint16_t left = _ppuLatch0 ? c[1] : c[0];\n"
    "\t\t\tuint16_t right = _ppuLatch1 ? c[5] : c[4];\n"
    "\t\t\tSelectChrPage4x(0, left & ~3, ChrMemoryType::ChrRam);\n"
    "\t\t\tSelectChrPage4x(1, right & ~3, ChrMemoryType::ChrRam);\n"
    "\t\t\treturn;\n"
    "\t\t}\n\n"
    "\t\tswitch(_chrMode & 7) {",
    "MMC2 CHR latch",
)

once(
    "\t\t\t\t// Special initialization required by a few internal mapper modes.\n"
    "\t\t\t\tif(_mapper == 0x11) _prg[2] = 0xFD;\n"
    "\t\t\t\tif(_mapper == 0x17) _mapRomOn6000 = true;\n"
    "\t\t\t\tif(_mapper == 0x0E) _prg[2] = 1;",
    "\t\t\t\t// Special initialization required by a few internal mapper modes.\n"
    "\t\t\t\t_mmc1Load = 0x20; _ppuLatch0 = false; _ppuLatch1 = false;\n"
    "\t\t\t\tif(_mapper == 0x11) _prg[2] = 0xFD;\n"
    "\t\t\t\t_mapRomOn6000 = (_mapper == 0x17);\n"
    "\t\t\t\tif(_mapper == 0x0E) _prg[2] = 1;",
    "mapper select init",
)

helper_marker = "\tvoid ResetRegisters()\n\t{"
helper = r'''\tvoid WriteMmc1(uint16_t addr, uint8_t value)
\t{
\t\tif(value & 0x80) {
\t\t\t_mmc1Load = 0x20;
\t\t\t_prgMode = 0;
\t\t\t_prg[3] = (_prg[3] & ~0x1E) | 0x1E;
\t\t\tSyncPrg();
\t\t\treturn;
\t\t}
\t\t_mmc1Load = (uint8_t)(((value & 1) << 5) | (_mmc1Load >> 1));
\t\tif(!(_mmc1Load & 1)) return;
\t\tuint8_t data = (_mmc1Load >> 1) & 0x1F;
\t\tswitch((addr >> 13) & 3) {
\t\t\tcase 0: {
\t\t\t\tuint8_t mode = (data >> 2) & 3;
\t\t\t\tif(mode == 3) { _prgMode = 0; _prg[3] = (_prg[3] & ~0x1E) | 0x1E; }
\t\t\t\telse if(mode == 2) { _prgMode = 1; _prg[3] &= ~0x1E; }
\t\t\t\telse _prgMode = 7;
\t\t\t\t_chrMode = (data & 0x10) ? 4 : 0;
\t\t\t\t_mirroring = (data & 3) ^ 2;
\t\t\t\tbreak;
\t\t\t}
\t\t\tcase 1:
\t\t\t\t_chr[0] = (_chr[0] & ~0x7C) | ((uint16_t)data << 2);
\t\t\t\tif(_flags & 1) _sramPage = (uint8_t)(2 | ((data & 8) ? 0 : 1));
\t\t\t\t_prg[1] = (_prg[1] & ~0x20) | ((data & 0x10) << 1);
\t\t\t\t_prg[3] = (_prg[3] & ~0x20) | ((data & 0x10) << 1);
\t\t\t\tbreak;
\t\t\tcase 2: _chr[4] = (_chr[4] & ~0x7C) | ((uint16_t)data << 2); break;
\t\t\tcase 3:
\t\t\t\t_prg[1] = (_prg[1] & ~0x1E) | ((data & 0x0F) << 1);
\t\t\t\t_sramEnabled = (data & 0x10) == 0;
\t\t\t\tbreak;
\t\t}
\t\t_mmc1Load = 0x20;
\t\tSync();
\t}

\tvoid WriteSimpleMapper(uint16_t addr, uint8_t value)
\t{
\t\tswitch(_mapper) {
\t\t\tcase 0x00: return; // NROM
\t\t\tcase 0x01: // 2/71/30
\t\t\t\t_prg[1] = (_prg[1] & 1) | ((value & 0x1F) << 1);
\t\t\t\tif((_flags & 1) && addr >= 0x9000 && addr <= 0x9FFF) _mirroring = (value & 0x10) ? 3 : 2;
\t\t\t\tif(_flags & 2) { _chr[0] = (_chr[0] & ~0x18) | ((value & 0x60) >> 2); _mirroring = (value & 0x80) ? 3 : 2; }
\t\t\t\tSync(); return;
\t\t\tcase 0x02: _chr[0] = (_chr[0] & 0x100) | ((value & 0x1F) << 3); SyncChr(); return; // CNROM
\t\t\tcase 0x03: // 78
\t\t\t\t_prg[1] = (_prg[1] & ~0x0E) | ((value & 7) << 1);
\t\t\t\t_chr[0] = (_chr[0] & ~0x78) | ((uint16_t)(value >> 4) << 3);
\t\t\t\t_mirroring = (value & 8) ? 0 : 1; Sync(); return;
\t\t\tcase 0x04: // 97
\t\t\t\t_prg[1] = (_prg[1] & ~0x3E) | ((value & 0x1F) << 1);
\t\t\t\t_mirroring = (value & 0x80) ? 0 : 1; Sync(); return;
\t\t\tcase 0x05: _prg[1] = (_prg[1] & ~0x0E) | (((value >> 4) & 7) << 1); _canWriteChr = value & 1; SyncPrg(); return; // 93
\t\t\tcase 0x08: // 7/34
\t\t\t\t_prg[1] = (_prg[1] & 3) | ((value & 0x0F) << 2);
\t\t\t\tif(!(_flags & 1)) _mirroring = (value & 0x10) ? 3 : 2; Sync(); return;
\t\t\tcase 0x0A: _prg[1] = (_prg[1] & ~0x0C) | ((value & 3) << 2); _chr[0] = (_chr[0] & ~0x78) | ((uint16_t)(value >> 4) << 3); Sync(); return; // 11
\t\t\tcase 0x0B: _prg[1] = (_prg[1] & ~0x0C) | (((value >> 4) & 3) << 2); _chr[0] = (_chr[0] & ~0x18) | ((uint16_t)(value & 3) << 3); Sync(); return; // 66
\t\t\tcase 0x0C: // 87
\t\t\t\tif(addr >= 0x6000 && addr <= 0x7FFF) { uint8_t b = ((value & 1) << 1) | ((value >> 1) & 1); _chr[0] = (_chr[0] & ~0x18) | ((uint16_t)b << 3); SyncChr(); }
\t\t\t\treturn;
\t\t\tcase 0x10: WriteMmc1(addr, value); return;
\t\t\tcase 0x11: // 9/10
\t\t\t\tswitch(addr & 0xF000) {
\t\t\t\t\tcase 0xA000: if(_flags & 1) _prg[1] = (_prg[1] & ~0x1E) | ((value & 0x0F) << 1); else _prg[1] = (_prg[1] & ~0x0F) | (value & 0x0F); break;
\t\t\t\t\tcase 0xB000: _chr[0] = (_chr[0] & ~0x7C) | ((uint16_t)(value & 0x1F) << 2); break;
\t\t\t\t\tcase 0xC000: _chr[1] = (_chr[1] & ~0x7C) | ((uint16_t)(value & 0x1F) << 2); break;
\t\t\t\t\tcase 0xD000: _chr[4] = (_chr[4] & ~0x7C) | ((uint16_t)(value & 0x1F) << 2); break;
\t\t\t\t\tcase 0xE000: _chr[5] = (_chr[5] & ~0x7C) | ((uint16_t)(value & 0x1F) << 2); break;
\t\t\t\t\tcase 0xF000: _mirroring = value & 1; break;
\t\t\t\t}
\t\t\t\tSync(); return;
\t\t\tcase 0x12: // 70/152
\t\t\t\t_chr[0] = (_chr[0] & ~0x78) | ((uint16_t)(value & 0x0F) << 3);
\t\t\t\t_prg[1] = (_prg[1] & ~0x0E) | (((value >> 4) & 7) << 1);
\t\t\t\tif(_flags & 1) _mirroring = (value & 0x80) ? 3 : 2; else _prg[1] = (_prg[1] & ~0x10) | ((value & 0x80) >> 3);
\t\t\t\tSync(); return;
\t\t}
\t}

\tvoid ResetRegisters()
\t{'''.replace('\\t', '\t')
once(helper_marker, helper, "mapper helpers")

once(
    "\t\t_lockout = false;\n\t\t_mmc3Sel = 0;",
    "\t\t_lockout = false;\n\t\t_mmc1Load = 0x20;\n\t\t_ppuLatch0 = false;\n\t\t_ppuLatch1 = false;\n\t\t_mmc3Sel = 0;",
    "reset extra state",
)
once(
    "\t\tSV(_sramEnabled); SV(_canWriteChr); SV(_canWriteFlash); SV(_fourScreen); SV(_mapRomOn6000); SV(_lockout);\n\t\tSV(_mmc3Sel);",
    "\t\tSV(_sramEnabled); SV(_canWriteChr); SV(_canWriteFlash); SV(_fourScreen); SV(_mapRomOn6000); SV(_lockout);\n\t\tSV(_mmc1Load); SV(_ppuLatch0); SV(_ppuLatch1);\n\t\tSV(_mmc3Sel);",
    "serialize extra state",
)

old_simple = '''\t\t// Common internal mapper modes.  The menu itself runs in the power-on
\t\t// NROM-style mode; these handlers cover the most common launched games.
\t\tif(_mapper == 0x00) return; // NROM

\t\tif(_mapper == 0x01) { // UxROM / mapper 2 family
\t\t\t_prg[1] = (_prg[1] & 1) | ((value & 0x1F) << 1);
\t\t\tSyncPrg();
\t\t\treturn;
\t\t}

\t\tif(_mapper == 0x02) { // CNROM
\t\t\t_chr[0] = (_chr[0] & 0x100) | ((value & 0x1F) << 3);
\t\t\tSyncChr();
\t\t\treturn;
\t\t}

'''.replace('\\t', '\t')
once(old_simple, "", "old simple handlers")

once(
    "\t\t\t}\n\t\t}\n\t}\n\npublic:\n\tvoid Reset(bool softReset) override",
    "\t\t\t}\n\t\t\treturn;\n\t\t}\n\n\t\tWriteSimpleMapper(addr, value);\n\t}\n\npublic:\n\tvoid Reset(bool softReset) override",
    "dispatch simple handlers",
)

once(
    "\tvoid NotifyVramAddressChange(uint16_t addr) override\n\t{\n\t\tif(_mapper != 0x14 || !IsA12RisingEdge(addr)) return;",
    "\tvoid NotifyVramAddressChange(uint16_t addr) override\n\t{\n"
    "\t\tif(_mapper == 0x11) {\n"
    "\t\t\tbool changed = false;\n"
    "\t\t\tif((addr & 0x1FF8) == 0x0FD8) { if(_ppuLatch0) { _ppuLatch0 = false; changed = true; } }\n"
    "\t\t\telse if((addr & 0x1FF8) == 0x0FE8) { if(!_ppuLatch0) { _ppuLatch0 = true; changed = true; } }\n"
    "\t\t\telse if((addr & 0x1FF8) == 0x1FD8) { if(_ppuLatch1) { _ppuLatch1 = false; changed = true; } }\n"
    "\t\t\telse if((addr & 0x1FF8) == 0x1FE8) { if(!_ppuLatch1) { _ppuLatch1 = true; changed = true; } }\n"
    "\t\t\tif(changed) SyncChr();\n"
    "\t\t}\n\n"
    "\t\tif(_mapper != 0x14 || !IsA12RisingEdge(addr)) return;",
    "MMC2 latch hook",
)

p.write_text(s, encoding="utf-8", newline="\n")
print("CoolGirl342 internal mapper support expanded")
