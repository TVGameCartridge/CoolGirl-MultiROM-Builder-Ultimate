from pathlib import Path
import re
import sys
import urllib.request

root = Path(sys.argv[1]).resolve()
src = root / "src"
boards = src / "boards"

FCEUMM_SHA = "7a542dab1e87679921962a9f056186eca425c0c2"
RAW = f"https://raw.githubusercontent.com/libretro/libretro-fceumm/{FCEUMM_SHA}/src/boards/"


def read(path):
    return path.read_text(encoding="utf-8", errors="ignore")


def write(path, text):
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
    print("patched:", path.relative_to(root))


def fetch_board(name):
    url = RAW + name
    print("fetch:", url)
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read().decode("utf-8")


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"mapper patch marker not found: {label}")
    return text.replace(old, new, 1)


# These small boards use the same FCEU/MMC3 board API as the pinned FCEUX.
# Pin the exact FCEUmm source revision so their behaviour cannot drift.
ports = {
    "830134C.c": "830134C.cpp",   # mapper 315
    "gn26.c": "gn26.cpp",         # mapper 344
    "393.c": "393.cpp",           # mapper 393
    "395.c": "395.cpp",           # mapper 395
    "359.c": "359.cpp",           # mapper 540 (shared source with 359)
}
for upstream, local in ports.items():
    write(boards / local, fetch_board(upstream))

# Mapper 358 is another J.Y. ASIC variant.  Do not replace FCEUX's complete
# 90/209/211 implementation with a newer FCEUmm core: the newer core uses APIs
# that are not present in this pinned FCEUX revision.  Instead add mapper 358's
# banking rules to the native 90.cpp core.
m90_path = boards / "90.cpp"
m90 = read(m90_path)

m90 = replace_once(
    m90,
    "static int is209;\nstatic int is211;",
    "static int is209;\nstatic int is211;\nstatic int is358;",
    "90.cpp mapper flags",
)

mapper358_helpers = r'''
/* NES 2.0 mapper 358 (J.Y. YY860606C) banking.  The formulas are ported
 * from FCEUmm jyasic.c, while keeping this FCEUX revision's native core. */
static uint8 rev7_358(uint8 v)
{
  return ((v << 6) & 0x40) | ((v << 4) & 0x20) | ((v << 2) & 0x10) |
         (v & 0x08) | ((v >> 2) & 0x04) | ((v >> 4) & 0x02) |
         ((v >> 6) & 0x01);
}

static void tekprom358(void)
{
  uint32 mask = 0x1F;
  uint32 bank = (tkcom[3] << 4) & ~0x1F;
  uint8 last = (tkcom[0] & 0x04) ? prgb[3] : 0xFF;
  uint8 p6000 = 0;

  switch (tkcom[0] & 3)
  {
    case 0:
      setprg32(0x8000, ((last & mask) | bank) >> 2);
      p6000 = (prgb[3] << 2) | 3;
      break;
    case 1:
      setprg16(0x8000, ((prgb[1] & mask) | bank) >> 1);
      setprg16(0xC000, ((last & mask) | bank) >> 1);
      p6000 = (prgb[3] << 1) | 1;
      break;
    case 2:
      setprg8(0x8000, (prgb[0] & mask) | bank);
      setprg8(0xA000, (prgb[1] & mask) | bank);
      setprg8(0xC000, (prgb[2] & mask) | bank);
      setprg8(0xE000, (last & mask) | bank);
      p6000 = prgb[3];
      break;
    case 3:
      setprg8(0x8000, (rev7_358(prgb[0]) & mask) | bank);
      setprg8(0xA000, (rev7_358(prgb[1]) & mask) | bank);
      setprg8(0xC000, (rev7_358(prgb[2]) & mask) | bank);
      setprg8(0xE000, (rev7_358(last) & mask) | bank);
      p6000 = rev7_358(prgb[3]);
      break;
  }

  if (tkcom[0] & 0x80)
    setprg8(0x6000, (p6000 & mask) | bank);
}

static void tekvrom358(void)
{
  int x;
  uint32 mask, bank;
  if (tkcom[3] & 0x20)
  {
    mask = 0x1FF;
    bank = (tkcom[3] << 7) & 0x600;
  }
  else
  {
    mask = 0x0FF;
    bank = ((tkcom[3] << 8) & 0x100) | ((tkcom[3] << 7) & 0x600);
  }

  switch (tkcom[0] & 0x18)
  {
    case 0x00:
      setchr8((((chrlow[0] | (chrhigh[0] << 8)) & mask) | bank) >> 3);
      break;
    case 0x08:
      if (tkcom[3] & 0x80)
      {
        setchr4(0x0000, (((chrlow[chr[0]] | (chrhigh[chr[0]] << 8)) & mask) | bank) >> 2);
        setchr4(0x1000, (((chrlow[chr[1]] | (chrhigh[chr[1]] << 8)) & mask) | bank) >> 2);
      }
      else
      {
        setchr4(0x0000, (((chrlow[0] | (chrhigh[0] << 8)) & mask) | bank) >> 2);
        setchr4(0x1000, (((chrlow[4] | (chrhigh[4] << 8)) & mask) | bank) >> 2);
      }
      break;
    case 0x10:
      for (x = 0; x < 8; x += 2)
        setchr2(x << 10, (((chrlow[x] | (chrhigh[x] << 8)) & mask) | bank) >> 1);
      break;
    case 0x18:
      for (x = 0; x < 8; x++)
        setchr1(x << 10, ((chrlow[x] | (chrhigh[x] << 8)) & mask) | bank);
      break;
  }
}

static void mira358(void)
{
  int x;
  if ((tkcom[0] & 0x20) || (tkcom[1] & 0x08))
  {
    setmirrorw(names[0] & 1, names[1] & 1, names[2] & 1, names[3] & 1);
    if (tkcom[0] & 0x20)
    {
      uint32 mask, bank;
      if (tkcom[3] & 0x20)
      {
        mask = 0x1FF;
        bank = (tkcom[3] << 7) & 0x600;
      }
      else
      {
        mask = 0x0FF;
        bank = ((tkcom[3] << 8) & 0x100) | ((tkcom[3] << 7) & 0x600);
      }
      for (x = 0; x < 4; x++)
      {
        int rom = ((names[x] & 0x80) ^ (tkcom[2] & 0x80)) | (tkcom[0] & 0x40);
        if (rom)
          setntamem(CHRptr[0] + 0x400 * (((names[x] & mask) | bank) & CHRmask1[0]), 0, x);
      }
    }
  }
  else
  {
    switch (tkcom[1] & 3)
    {
      case 0: setmirror(MI_V); break;
      case 1: setmirror(MI_H); break;
      case 2: setmirror(MI_0); break;
      case 3: setmirror(MI_1); break;
    }
  }
}

'''

m90 = replace_once(
    m90,
    "static void mira(void)\n{",
    mapper358_helpers + "static void mira(void)\n{\n  if(is358)\n  {\n    mira358();\n    return;\n  }",
    "90.cpp mira",
)

m90 = replace_once(
    m90,
    "static void tekprom(void)\n{",
    "static void tekprom(void)\n{\n  if(is358)\n  {\n    tekprom358();\n    return;\n  }",
    "90.cpp tekprom",
)

m90 = replace_once(
    m90,
    "static void tekvrom(void)\n{",
    "static void tekvrom(void)\n{\n  if(is358)\n  {\n    tekvrom358();\n    return;\n  }",
    "90.cpp tekvrom",
)

# Mapper 358 has MMC4-style latches only when D003.7 is enabled and CHR mode
# is 4 KiB.  Existing mapper 209 behaviour remains untouched.
ppu_marker = "static void M90PPU(uint32 A)\n{\n  if((IRQMode&3)==2)"
ppu_repl = "static void M90PPU(uint32 A)\n{\n  if(is358 && (tkcom[3]&0x80) && ((tkcom[0]&0x18)==0x08) && (((A&0x2FF0)==0x0FD0) || ((A&0x2FF0)==0x0FE0) || ((A&0x2FF0)==0x1FD0) || ((A&0x2FF0)==0x1FE0)))\n  {\n    chr[(A>>12)&1]=((A>>10)&4)|((A>>4)&2);\n    tekvrom();\n  }\n\n  if((IRQMode&3)==2)"
m90 = replace_once(m90, ppu_marker, ppu_repl, "90.cpp PPU hook")

# Use the full D000-D7FF mode-register decode for mapper 358.
m90 = replace_once(
    m90,
    "  SetWriteHandler(0xD000,0xD5ff,M90ModeWrite);",
    "  if(is358) SetWriteHandler(0xD000,0xD7ff,M90ModeWrite);\n  else SetWriteHandler(0xD000,0xD5ff,M90ModeWrite);",
    "90.cpp mode handler range",
)

# FCEUmm initializes mapper 358's registers to zero and latches to 0/4.
power_marker = "  memset(tkcom,0x00,sizeof(tkcom));\n  memset(prgb,0xff,sizeof(prgb));\n  memset(chrlow,0xff,sizeof(chrlow));\n  memset(chrhigh,0xff,sizeof(chrhigh));\n  memset(names,0x00,sizeof(names));"
power_repl = "  memset(tkcom,0x00,sizeof(tkcom));\n  if(is358)\n  {\n    memset(prgb,0x00,sizeof(prgb));\n    memset(chrlow,0x00,sizeof(chrlow));\n    memset(chrhigh,0x00,sizeof(chrhigh));\n    chr[0]=0; chr[1]=4;\n  }\n  else\n  {\n    memset(prgb,0xff,sizeof(prgb));\n    memset(chrlow,0xff,sizeof(chrlow));\n    memset(chrhigh,0xff,sizeof(chrhigh));\n  }\n  memset(names,0x00,sizeof(names));"
m90 = replace_once(m90, power_marker, power_repl, "90.cpp power init")

# Make every mapper init set all variant flags deterministically, then add 358.
m90 = replace_once(m90, "  is211=0;\n  is209=0;\n  info->Reset=togglie;", "  is211=0;\n  is209=0;\n  is358=0;\n  info->Reset=togglie;", "Mapper90 flags")
m90 = replace_once(m90, "  is211=0;\n  is209=1;\n  info->Reset=togglie;", "  is211=0;\n  is209=1;\n  is358=0;\n  info->Reset=togglie;", "Mapper209 flags")
m90 = replace_once(m90, "void Mapper211_Init(CartInfo *info)\n{\n  is211=1;", "void Mapper211_Init(CartInfo *info)\n{\n  is211=1;\n  is209=0;\n  is358=0;", "Mapper211 flags")

mapper358_init = r'''

void Mapper358_Init(CartInfo *info)
{
  is211=0;
  is209=0;
  is358=1;
  info->Reset=togglie;
  info->Power=M90Power;
  PPU_hook=M90PPU;
  MapIRQHook=CPUWrap;
  GameHBIRQHook2=SLWrap;
  GameStateRestore=M90Restore;
  AddExState(Tek_StateRegs, ~0, 0, 0);
}
'''
if "void Mapper358_Init(CartInfo *info)" not in m90:
    m90 += mapper358_init
write(m90_path, m90)

# Compile the additional board sources.  90.cpp is already in the list.
cmake = read(src / "CMakeLists.txt")
new_sources = [
    "${CMAKE_CURRENT_SOURCE_DIR}/boards/830134C.cpp",
    "${CMAKE_CURRENT_SOURCE_DIR}/boards/gn26.cpp",
    "${CMAKE_CURRENT_SOURCE_DIR}/boards/393.cpp",
    "${CMAKE_CURRENT_SOURCE_DIR}/boards/395.cpp",
    "${CMAKE_CURRENT_SOURCE_DIR}/boards/359.cpp",
]
if new_sources[0] not in cmake:
    marker = "${CMAKE_CURRENT_SOURCE_DIR}/boards/90.cpp"
    if marker not in cmake:
        raise SystemExit("CMake board marker not found")
    addition = marker + "\n\t" + "\n\t".join(new_sources)
    cmake = cmake.replace(marker, addition, 1)
    write(src / "CMakeLists.txt", cmake)
else:
    print("mapper sources already present in CMakeLists.txt")

# Add prototypes for newly imported iNES mapper entry points.
ines_h_path = src / "ines.h"
ines_h = read(ines_h_path)
protos = [
    "void BMC830134C_Init(CartInfo *);",
    "void BMCGN26_Init(CartInfo *);",
    "void Mapper358_Init(CartInfo *);",
    "void Mapper393_Init(CartInfo *);",
    "void Mapper395_Init(CartInfo *);",
    "void Mapper540_Init(CartInfo *);",
]
missing = [p for p in protos if p not in ines_h]
if missing:
    pos = ines_h.rfind("#endif")
    if pos < 0:
        raise SystemExit("ines.h #endif not found")
    ines_h = ines_h[:pos] + "\n/* CGEMU342 extra NES 2.0 mappers */\n" + "\n".join(missing) + "\n\n" + ines_h[pos:]
    write(ines_h_path, ines_h)
else:
    print("mapper prototypes already present")

# Register mapper numbers. UNLYOKO_Init and BMC411120C_Init are already
# declared by unif.h and implemented by the pinned FCEUX source.
ines_cpp_path = src / "ines.cpp"
ines_cpp = read(ines_cpp_path)
entries = [
    ('"YOKO (NES 2.0)"', 264, "UNLYOKO_Init"),
    ('"BMC-411120-C"', 287, "BMC411120C_Init"),
    ('"BMC-830134C"', 315, "BMC830134C_Init"),
    ('"BMC-GN-26"', 344, "BMCGN26_Init"),
    ('"JY YY860606C"', 358, "Mapper358_Init"),
    ('"BMC-820720C"', 393, "Mapper393_Init"),
    ('"REALTEC 8210"', 395, "Mapper395_Init"),
    ('"UNL-82112C"', 540, "Mapper540_Init"),
]
missing_entries = []
for name, number, init in entries:
    if not re.search(r"\{[^\n]*,\s*" + str(number) + r"\s*,", ines_cpp):
        missing_entries.append(f"\t{{{name},\t{number}, {init}}},")

if missing_entries:
    marker = re.search(r"(?m)^\s*\{\"COOLGIRL\"[^\n]*$", ines_cpp)
    if not marker:
        raise SystemExit("iNES mapper table marker COOLGIRL not found")
    block = "\n".join(missing_entries) + "\n"
    ines_cpp = ines_cpp[:marker.start()] + block + ines_cpp[marker.start():]
    write(ines_cpp_path, ines_cpp)
else:
    print("mapper table entries already present")

print("MAPPER PATCH COMPLETE: 45(existing), 264, 287, 315, 344, 358, 393, 395, 540")
