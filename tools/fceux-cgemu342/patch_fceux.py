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

needle = "\t// Parse the commandline arguments\n\tt = ParseArgies(argc, argv);\n"
replacement = "\t// Parse the commandline arguments\n\tt = ParseArgies(argc, argv);\n\n\tCGEMU342_Init(BaseDirectory.c_str());\n\tstd::string cgemu342AutoMenu;\n\tif (!t)\n\t{\n\t\tcgemu342AutoMenu = BaseDirectory + \"\\\\multirom.nes\";\n\t\tDWORD attrs = GetFileAttributesA(cgemu342AutoMenu.c_str());\n\t\tif (attrs != INVALID_FILE_ATTRIBUTES && !(attrs & FILE_ATTRIBUTE_DIRECTORY))\n\t\t\tt = (char*)cgemu342AutoMenu.c_str();\n\t}\n"
if 'CGEMU342_Init(BaseDirectory.c_str());' not in text:
    if needle not in text:
        raise SystemExit("main startup insertion point not found")
    text = text.replace(needle, replacement, 1)

needle = "\tif (t)\n\t{\n\t\tALoad(t);\n\t} else\n"
replacement = "\tif (t)\n\t{\n\t\tif (ALoad(t) && CGEMU342_IsContainer(t))\n\t\t\tFCEU_LoadLuaCode(\"::CGEMU342_INTERNAL::\");\n\t} else\n"
if 'FCEU_LoadLuaCode("::CGEMU342_INTERNAL::");' not in text:
    if needle not in text:
        raise SystemExit("main initial ALoad insertion point not found")
    text = text.replace(needle, replacement, 1)
main.write_text(text, encoding="utf-8", newline="\n")
print("patched: src/drivers/win/main.cpp")

lua = root / "src" / "lua-engine.cpp"
text = lua.read_text(encoding="utf-8-sig")
if '#include "cgemu342.h"' not in text:
    needle = '#include "fceulua.h"\n'
    if needle not in text:
        raise SystemExit("lua-engine include insertion point not found")
    text = text.replace(needle, needle + '#include "cgemu342.h"\n', 1)

needle = "int FCEU_LoadLuaCode(const char *filename, const char *arg) \n{\n\tif (!DemandLua())\n"
replacement = "int FCEU_LoadLuaCode(const char *filename, const char *arg) \n{\n\tconst bool cgemu342Embedded = filename && !strcmp(filename, \"::CGEMU342_INTERNAL::\");\n\tif (!DemandLua())\n"
if 'const bool cgemu342Embedded' not in text:
    if needle not in text:
        raise SystemExit("lua-engine function insertion point not found")
    text = text.replace(needle, replacement, 1)

needle = "\tstd::string getfilepath = filename;\n\n\tgetfilepath = getfilepath.substr(0,getfilepath.find_last_of(\"/\\\\\") + 1);\n\n\tif ( SetCurrentDir(getfilepath.c_str()) != 0 )\n"
replacement = "\tstd::string getfilepath = cgemu342Embedded ? CGEMU342_BaseDirectory() : filename;\n\n\tif (!cgemu342Embedded)\n\t\tgetfilepath = getfilepath.substr(0,getfilepath.find_last_of(\"/\\\\\") + 1);\n\n\tif ( SetCurrentDir(getfilepath.c_str()) != 0 )\n"
if 'cgemu342Embedded ? CGEMU342_BaseDirectory()' not in text:
    if needle not in text:
        raise SystemExit("lua-engine cwd insertion point not found")
    text = text.replace(needle, replacement, 1)

needle = "\t// Load the data\n\tint result = luaL_loadfile(L,filename);\n"
replacement = "\t// Load the data. CGEMU342 is compiled into the executable as an internal Lua chunk.\n\tint result = cgemu342Embedded\n\t\t? luaL_loadbuffer(L, CGEMU342_EmbeddedLuaSource(),\n\t\t\tstrlen(CGEMU342_EmbeddedLuaSource()), CGEMU342_EmbeddedLuaChunkName())\n\t\t: luaL_loadfile(L,filename);\n"
if 'luaL_loadbuffer(L, CGEMU342_EmbeddedLuaSource()' not in text:
    if needle not in text:
        raise SystemExit("lua-engine load insertion point not found")
    text = text.replace(needle, replacement, 1)

needle = "#ifdef __WIN_DRIVER__\n\tAddRecentLuaFile(filename); //Add the filename to our recent lua menu\n#endif\n"
replacement = "#ifdef __WIN_DRIVER__\n\tif (!cgemu342Embedded)\n\t\tAddRecentLuaFile(filename); // external scripts only\n#endif\n"
if 'if (!cgemu342Embedded)\n\t\tAddRecentLuaFile' not in text:
    if needle not in text:
        raise SystemExit("lua-engine recent insertion point not found")
    text = text.replace(needle, replacement, 1)

needle = "#ifdef __WIN_DRIVER__\n\tinfo_print = PrintToWindowConsole;\n\tinfo_onstart = WinLuaOnStart;\n\tinfo_onstop = WinLuaOnStop;\n\tif(!LuaConsoleHWnd)\n\t\tLuaConsoleHWnd = CreateDialog(fceu_hInstance, MAKEINTRESOURCE(IDD_LUA), hAppWnd, DlgLuaScriptDialog);\n\tinfo_uid = (intptr_t)LuaConsoleHWnd;\n#else\n"
replacement = "#ifdef __WIN_DRIVER__\n\tinfo_print = PrintToWindowConsole;\n\tif (cgemu342Embedded)\n\t{\n\t\t// Internal CGEMU342 launcher: no Lua Script window and no recent-script entry.\n\t\tinfo_onstart = nullptr;\n\t\tinfo_onstop = nullptr;\n\t\tinfo_uid = (intptr_t)0;\n\t}\n\telse\n\t{\n\t\tinfo_onstart = WinLuaOnStart;\n\t\tinfo_onstop = WinLuaOnStop;\n\t\tif(!LuaConsoleHWnd)\n\t\t\tLuaConsoleHWnd = CreateDialog(fceu_hInstance, MAKEINTRESOURCE(IDD_LUA), hAppWnd, DlgLuaScriptDialog);\n\t\tinfo_uid = (intptr_t)LuaConsoleHWnd;\n\t}\n#else\n"
if 'Internal CGEMU342 launcher: no Lua Script window' not in text:
    if needle not in text:
        raise SystemExit("lua-engine window insertion point not found")
    text = text.replace(needle, replacement, 1)

lua.write_text(text, encoding="utf-8", newline="\n")
print("patched: src/lua-engine.cpp")
print("PATCH COMPLETE")
