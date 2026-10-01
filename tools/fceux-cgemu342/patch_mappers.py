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


# FCEUmm is derived from the same FCEU codebase.  Pin the exact source
# revision so these mapper implementations cannot silently change.
ports = {
    "830134C.c": "830134C.cpp",   # mapper 315
    "gn26.c": "gn26.cpp",         # mapper 344
    "393.c": "393.cpp",           # mapper 393
    "395.c": "395.cpp",           # mapper 395
    "359.c": "359.cpp",           # mapper 540 (shared source with 359)
}

for upstream, local in ports.items():
    write(boards / local, fetch_board(upstream))

# Mapper 358 is a J.Y. ASIC variant.  The old pinned FCEUX 90.cpp only has
# 90/209/211; current FCEUmm's jyasic implementation is the compatible
# continuation and also retains those old mapper entry points.
jy = fetch_board("jyasic.c")
write(boards / "90.cpp", jy)

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
    # Match the numeric mapper field, not incidental text elsewhere.
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
