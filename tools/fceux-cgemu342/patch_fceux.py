from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
helper = Path(__file__).resolve().parent

for name in ("cgemu342.cpp", "cgemu342.h"):
    (root / "src" / name).write_text((helper / name).read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    print("installed: src/" + name)

proj = root / "vc" / "vc14_fceux.vcxproj"
text = proj.read_text(encoding="utf-8-sig")
if '..\\src\\cgemu342.cpp' not in text:
    needle = '    <ClCompile Include="..\\src\\drivers\\common\\args.cpp" />'
    if needle not in text:
        raise SystemExit("vcxproj compile insertion point not found")
    text = text.replace(needle, '    <ClCompile Include="..\\src\\cgemu342.cpp" />\n' + needle, 1)
proj.write_text(text, encoding="utf-8", newline="\n")
print("patched: vc/vc14_fceux.vcxproj")

main = root / "src" / "drivers" / "win" / "main.cpp"
text = main.read_text(encoding="utf-8-sig")
if '#include "../../cgemu342.h"' not in text:
    needle = '#include "../../fceulua.h"\n'
    if needle not in text:
        raise SystemExit("main include insertion point not found")
    text = text.replace(needle, needle + '#include "../../cgemu342.h"\n', 1)

needle = '''\t// Parse the commandline arguments\n\tt = ParseArgies(argc, argv);\n'''
replacement = '''\t// Parse the commandline arguments\n\tt = ParseArgies(argc, argv);\n\n\tCGEMU342_Init(BaseDirectory.c_str());\n\tstd::string cgemu342AutoMenu;\n\tif (!t)\n\t{\n\t\tcgemu342AutoMenu = BaseDirectory + "\\\\multirom.nes";\n\t\tDWORD attrs = GetFileAttributesA(cgemu342AutoMenu.c_str());\n\t\tif (attrs != INVALID_FILE_ATTRIBUTES && !(attrs & FILE_ATTRIBUTE_DIRECTORY))\n\t\t\tt = (char*)cgemu342AutoMenu.c_str();\n\t}\n'''
if 'CGEMU342_Init(BaseDirectory.c_str());' not in text:
    if needle not in text:
        raise SystemExit("main startup insertion point not found")
    text = text.replace(needle, replacement, 1)

needle = '''\tif (t)\n\t{\n\t\tALoad(t);\n\t} else\n'''
replacement = '''\tif (t)\n\t{\n\t\tif (ALoad(t))\n\t\t\tCGEMU342_OnRomLoaded(t);\n\t} else\n'''
if 'CGEMU342_OnRomLoaded(t);' not in text:
    if needle not in text:
        raise SystemExit("main initial ALoad insertion point not found")
    text = text.replace(needle, replacement, 1)
main.write_text(text, encoding="utf-8", newline="\n")
print("patched: src/drivers/win/main.cpp")

# This is the critical timing match. Lua resumes inside FCEUI_Emulate(),
# immediately after FCEU_StateRecorderUpdate() and before input/PPU emulation.
fceu = root / "src" / "fceu.cpp"
text = fceu.read_text(encoding="utf-8-sig")
if '#include "cgemu342.h"' not in text:
    needle = '#include "utils/crc32.h"\n'
    if needle not in text:
        raise SystemExit("fceu include insertion point not found")
    text = text.replace(needle, needle + '#include "cgemu342.h"\n', 1)
needle = '\tFCEU_StateRecorderUpdate();\n'
replacement = '\tFCEU_StateRecorderUpdate();\n\tCGEMU342_FrameBoundary();\n'
if 'CGEMU342_FrameBoundary();' not in text:
    if needle not in text:
        raise SystemExit("frame-boundary insertion point not found")
    text = text.replace(needle, replacement, 1)
fceu.write_text(text, encoding="utf-8", newline="\n")
print("patched: src/fceu.cpp")

# Hook mapper 342 writes so native launcher supports both the old $5FF0
# protocol and unmodified CoolGirl menu hand-off sequences.
coolgirl = root / "src" / "boards" / "coolgirl.cpp"
text = coolgirl.read_text(encoding="utf-8-sig")
if '#include "../cgemu342.h"' not in text:
    needle = '#include "mapinc.h"\n'
    if needle not in text:
        raise SystemExit("coolgirl include insertion point not found")
    text = text.replace(needle, needle + '#include "../cgemu342.h"\n', 1)
needle = 'static DECLFW(COOLGIRL_WRITE) {\n'
replacement = 'static DECLFW(COOLGIRL_WRITE) {\n\tCGEMU342_OnCoolGirlWrite(A, V);\n'
if 'CGEMU342_OnCoolGirlWrite(A, V);' not in text:
    if needle not in text:
        raise SystemExit("coolgirl write insertion point not found")
    text = text.replace(needle, replacement, 1)
coolgirl.write_text(text, encoding="utf-8", newline="\n")
print("patched: src/boards/coolgirl.cpp")

print("PATCH COMPLETE")
