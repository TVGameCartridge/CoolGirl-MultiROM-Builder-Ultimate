from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
helper = Path(__file__).resolve().parent

# Install native launcher module into the FCEUX core source directory.
for name in ("cgemu342.cpp", "cgemu342.h"):
    (root / "src" / name).write_text((helper / name).read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    print("installed: src/" + name)

# Add native module to the classic Windows Visual Studio project.
proj = root / "vc" / "vc14_fceux.vcxproj"
text = proj.read_text(encoding="utf-8-sig")
if '..\\src\\cgemu342.cpp' not in text:
    needle = '    <ClCompile Include="..\\src\\drivers\\common\\args.cpp" />'
    if needle not in text:
        raise SystemExit("vcxproj compile insertion point not found")
    text = text.replace(needle, '    <ClCompile Include="..\\src\\cgemu342.cpp" />\n' + needle, 1)
proj.write_text(text, encoding="utf-8", newline="\n")
print("patched: vc/vc14_fceux.vcxproj")

# Integrate with the classic Win32 driver only. This keeps normal FCEUX mapper loading intact.
main = root / "src" / "drivers" / "win" / "main.cpp"
text = main.read_text(encoding="utf-8-sig")
if '#include "../../cgemu342.h"' not in text:
    needle = '#include "../../fceulua.h"\n'
    if needle not in text:
        raise SystemExit("main include insertion point not found")
    text = text.replace(needle, needle + '#include "../../cgemu342.h"\n', 1)

# Initialize adjacent multirom.nes after BaseDirectory is known and make it the implicit ROM.
needle = '''\t// Parse the commandline arguments\n\tt = ParseArgies(argc, argv);\n'''
replacement = '''\t// Parse the commandline arguments\n\tt = ParseArgies(argc, argv);\n\n\t// Native CGEMU342 launcher: when no ROM was supplied, automatically use\n\t// multirom.nes next to fceux.exe. Setting t here also preserves the\n\t// fullscreen value loaded from fceux.cfg (stock FCEUX forces it off when t is null).\n\tCGEMU342_Init(BaseDirectory.c_str());\n\tstd::string cgemu342AutoMenu;\n\tif (!t)\n\t{\n\t\tcgemu342AutoMenu = BaseDirectory + "\\\\multirom.nes";\n\t\tDWORD attrs = GetFileAttributesA(cgemu342AutoMenu.c_str());\n\t\tif (attrs != INVALID_FILE_ATTRIBUTES && !(attrs & FILE_ATTRIBUTE_DIRECTORY))\n\t\t\tt = (char*)cgemu342AutoMenu.c_str();\n\t}\n'''
if 'CGEMU342_Init(BaseDirectory.c_str());' not in text:
    if needle not in text:
        raise SystemExit("main startup insertion point not found")
    text = text.replace(needle, replacement, 1)

# Tell native launcher whether a loaded file is the CGEMU342 container.
needle = '''\tif (t)\n\t{\n\t\tALoad(t);\n\t} else\n'''
replacement = '''\tif (t)\n\t{\n\t\tif (ALoad(t))\n\t\t\tCGEMU342_OnRomLoaded(t);\n\t} else\n'''
if 'CGEMU342_OnRomLoaded(t);' not in text:
    if needle not in text:
        raise SystemExit("main initial ALoad insertion point not found")
    text = text.replace(needle, replacement, 1)

# Poll mailbox once per emulated frame and perform requested ROM switches only
# after FCEUI_Emulate has returned to the Windows driver.
needle = '''\t\t\tFCEUI_Emulate(&gfx, &sound, &ssize, skippy); //emulate a single frame\n\t\t\tFCEUD_Update(gfx, sound, ssize); //update displays and debug tools\n'''
replacement = '''\t\t\tFCEUI_Emulate(&gfx, &sound, &ssize, skippy); //emulate a single frame\n\t\t\tFCEUD_Update(gfx, sound, ssize); //update displays and debug tools\n\n\t\t\tCGEMU342_Poll();\n\t\t\tstd::string cgemu342NextRom;\n\t\t\tif (CGEMU342_TakePendingLoad(cgemu342NextRom))\n\t\t\t{\n\t\t\t\tif (ALoad(cgemu342NextRom.c_str()))\n\t\t\t\t\tCGEMU342_OnRomLoaded(cgemu342NextRom.c_str());\n\t\t\t}\n'''
if 'CGEMU342_TakePendingLoad(cgemu342NextRom)' not in text:
    if needle not in text:
        raise SystemExit("main frame insertion point not found")
    text = text.replace(needle, replacement, 1)

main.write_text(text, encoding="utf-8", newline="\n")
print("patched: src/drivers/win/main.cpp")
print("PATCH COMPLETE")
