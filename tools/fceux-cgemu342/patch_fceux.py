from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
helper = Path(__file__).resolve().parent

# Install native launcher module into the FCEUX core source directory.
for name in ("cgemu342.cpp", "cgemu342.h"):
    (root / "src" / name).write_text(
        (helper / name).read_text(encoding="utf-8"),
        encoding="utf-8",
        newline="\n",
    )
    print("installed: src/" + name)

# Add native module to the classic Windows Visual Studio project.
proj = root / "vc" / "vc14_fceux.vcxproj"
text = proj.read_text(encoding="utf-8-sig")
if '..\\src\\cgemu342.cpp' not in text:
    needle = '    <ClCompile Include="..\\src\\drivers\\common\\args.cpp" />'
    if needle not in text:
        raise SystemExit("vcxproj compile insertion point not found")
    text = text.replace(
        needle,
        '    <ClCompile Include="..\\src\\cgemu342.cpp" />\n' + needle,
        1,
    )
proj.write_text(text, encoding="utf-8", newline="\n")
print("patched: vc/vc14_fceux.vcxproj")

# Poll the native mailbox at the same core frame boundary where the Lua launcher
# resumes after emu.frameadvance(). This removes the timing difference between
# the Lua and native implementations.
fceu = root / "src" / "fceu.cpp"
text = fceu.read_text(encoding="utf-8-sig")
if '#include "cgemu342.h"' not in text:
    needle = '#include "fceulua.h"\n'
    if needle not in text:
        raise SystemExit("fceu include insertion point not found")
    text = text.replace(needle, needle + '#include "cgemu342.h"\n', 1)

needle = '''#ifdef _S9XLUA_H
\tFCEU_LuaFrameBoundary();
#endif

\tFCEU_UpdateInput();
'''
replacement = '''#ifdef _S9XLUA_H
\tFCEU_LuaFrameBoundary();
#endif

\t// Native equivalent of the old Lua launcher: inspect $07F0-$07F2
\t// at the same frame boundary before the next emulated frame runs.
\tCGEMU342_Poll();

\tFCEU_UpdateInput();
'''
if 'Native equivalent of the old Lua launcher' not in text:
    if needle not in text:
        raise SystemExit("fceu frame-boundary insertion point not found")
    text = text.replace(needle, replacement, 1)
fceu.write_text(text, encoding="utf-8", newline="\n")
print("patched: src/fceu.cpp")

# Integrate startup and deferred ROM switching with the classic Win32 driver.
main = root / "src" / "drivers" / "win" / "main.cpp"
text = main.read_text(encoding="utf-8-sig")
if '#include "../../cgemu342.h"' not in text:
    needle = '#include "../../fceulua.h"\n'
    if needle not in text:
        raise SystemExit("main include insertion point not found")
    text = text.replace(needle, needle + '#include "../../cgemu342.h"\n', 1)

# Initialize adjacent multirom.nes after BaseDirectory is known and make it the
# implicit ROM. Setting t here preserves fullscreen loaded from fceux.cfg.
needle = '''\t// Parse the commandline arguments
\tt = ParseArgies(argc, argv);
'''
replacement = '''\t// Parse the commandline arguments
\tt = ParseArgies(argc, argv);

\tCGEMU342_Init(BaseDirectory.c_str());
\tstd::string cgemu342AutoMenu;
\tif (!t)
\t{
\t\tcgemu342AutoMenu = BaseDirectory + "\\\\multirom.nes";
\t\tDWORD attrs = GetFileAttributesA(cgemu342AutoMenu.c_str());
\t\tif (attrs != INVALID_FILE_ATTRIBUTES && !(attrs & FILE_ATTRIBUTE_DIRECTORY))
\t\t\tt = (char*)cgemu342AutoMenu.c_str();
\t}
'''
if 'CGEMU342_Init(BaseDirectory.c_str());' not in text:
    if needle not in text:
        raise SystemExit("main startup insertion point not found")
    text = text.replace(needle, replacement, 1)

# Tell native launcher whether the initial loaded file is the CGEMU342 container.
needle = '''\tif (t)
\t{
\t\tALoad(t);
\t} else
'''
replacement = '''\tif (t)
\t{
\t\tif (ALoad(t))
\t\t\tCGEMU342_OnRomLoaded(t);
\t} else
'''
if 'CGEMU342_OnRomLoaded(t);' not in text:
    if needle not in text:
        raise SystemExit("main initial ALoad insertion point not found")
    text = text.replace(needle, replacement, 1)

# The core frame-boundary hook detects the mailbox. Only perform the actual ROM
# switch after FCEUI_Emulate has returned to the Win32 driver.
needle = '''\t\t\tFCEUI_Emulate(&gfx, &sound, &ssize, skippy); //emulate a single frame
\t\t\tFCEUD_Update(gfx, sound, ssize); //update displays and debug tools
'''
replacement = '''\t\t\tFCEUI_Emulate(&gfx, &sound, &ssize, skippy); //emulate a single frame
\t\t\tFCEUD_Update(gfx, sound, ssize); //update displays and debug tools

\t\t\tstd::string cgemu342NextRom;
\t\t\tif (CGEMU342_TakePendingLoad(cgemu342NextRom))
\t\t\t{
\t\t\t\tif (ALoad(cgemu342NextRom.c_str()))
\t\t\t\t\tCGEMU342_OnRomLoaded(cgemu342NextRom.c_str());
\t\t\t}
'''
if 'CGEMU342_TakePendingLoad(cgemu342NextRom)' not in text:
    if needle not in text:
        raise SystemExit("main frame insertion point not found")
    text = text.replace(needle, replacement, 1)

main.write_text(text, encoding="utf-8", newline="\n")
print("patched: src/drivers/win/main.cpp")
print("PATCH COMPLETE")
