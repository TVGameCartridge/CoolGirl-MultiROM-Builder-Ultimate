from pathlib import Path
import re, sys

root = Path(sys.argv[1]).resolve()
src = root / 'src'

def rw(path, fn):
    p = root / path
    s = p.read_text(encoding='utf-8', errors='ignore')
    n = fn(s)
    if n == s:
        print('unchanged:', path)
    else:
        p.write_text(n, encoding='utf-8', newline='\n')
        print('patched:', path)

# CMake: MinGW-native dependencies, no fake MSVC, use internal Lua.
def patch_cmake(s):
    old = '''if(WIN32)\n     find_package(OpenGL REQUIRED)\n     #find_package(Qt5 COMPONENTS Widgets OpenGL REQUIRED)\n     #add_definitions( ${Qt5Widgets_DEFINITIONS}  )\n     #include_directories( ${Qt5Widgets_INCLUDE_DIRS} )\n     add_definitions( -DMSVC -D_CRT_SECURE_NO_WARNINGS )\n     add_definitions( -D__SDL__  -D__QT_DRIVER__  -DQT_DEPRECATED_WARNINGS )\n     add_definitions( -DFCEUDEF_DEBUGGER )\n     add_definitions( -D_USE_LIBARCHIVE )\n     add_definitions( /wd4267 /wd4244 )\n     #add_definitions( /wd4018 ) # Integer comparison sign mismatch warnings\n     include_directories( ${SDL_INSTALL_PREFIX}/include )\n     include_directories( ${LIBARCHIVE_INSTALL_PREFIX}/include )\n     include_directories( ${CMAKE_CURRENT_SOURCE_DIR}/drivers/win/zlib )\n     set( OPENGL_LDFLAGS  OpenGL::GL )\n     set( SDL2_LDFLAGS  ${SDL_INSTALL_PREFIX}/lib/x64/SDL2.lib )\n     set( LIBARCHIVE_LDFLAGS  ${LIBARCHIVE_INSTALL_PREFIX}/lib/archive.lib )\n     set( SYS_LIBS  wsock32 ws2_32 vfw32 Htmlhelp )\n'''
    new = '''if(WIN32)\n     find_package(OpenGL REQUIRED)\n     add_definitions( -D_CRT_SECURE_NO_WARNINGS )\n     add_definitions( -D__SDL__  -D__QT_DRIVER__  -DQT_DEPRECATED_WARNINGS )\n     add_definitions( -DFCEUDEF_DEBUGGER )\n     set( OPENGL_LDFLAGS  OpenGL::GL )\n     set( SYS_LIBS  wsock32 ws2_32 vfw32 Htmlhelp )\n\n     if(MSVC)\n       add_definitions( -DMSVC -D_USE_LIBARCHIVE )\n       add_definitions( /wd4267 /wd4244 )\n       include_directories( ${SDL_INSTALL_PREFIX}/include )\n       include_directories( ${LIBARCHIVE_INSTALL_PREFIX}/include )\n       include_directories( ${CMAKE_CURRENT_SOURCE_DIR}/drivers/win/zlib )\n       set( SDL2_LDFLAGS  ${SDL_INSTALL_PREFIX}/lib/x64/SDL2.lib )\n       set( LIBARCHIVE_LDFLAGS  ${LIBARCHIVE_INSTALL_PREFIX}/lib/archive.lib )\n     else()\n       # Native MinGW/MSYS2 Windows build. Keep internal Lua.\n       add_definitions( -DPSS_STYLE=2 -D_USE_LIBARCHIVE -D_SYSTEM_MINIZIP )\n       find_package(PkgConfig REQUIRED)\n       find_package(ZLIB REQUIRED)\n       pkg_check_modules( MINIZIP REQUIRED minizip )\n       pkg_check_modules( LIBARCHIVE REQUIRED libarchive )\n       pkg_check_modules( SDL2 REQUIRED sdl2 )\n       add_definitions( ${SDL2_CFLAGS} ${LIBARCHIVE_CFLAGS} ${MINIZIP_CFLAGS} )\n       include_directories( ${SDL2_INCLUDE_DIRS} ${LIBARCHIVE_INCLUDE_DIRS} ${MINIZIP_INCLUDE_DIRS} )\n       set( SDL2_LDFLAGS ${SDL2_LDFLAGS} )\n       set( LIBARCHIVE_LDFLAGS ${LIBARCHIVE_LDFLAGS} )\n       set( MINIZIP_LDFLAGS ${MINIZIP_LDFLAGS} )\n     endif()\n'''
    if old not in s:
        raise SystemExit('Windows CMake block not found')
    s = s.replace(old, new, 1)
    if 'cgemu342.cpp' not in s:
        s = s.replace('${CMAKE_CURRENT_SOURCE_DIR}/fceu.cpp', '${CMAKE_CURRENT_SOURCE_DIR}/fceu.cpp\n\t${CMAKE_CURRENT_SOURCE_DIR}/cgemu342.cpp', 1)
    return s
rw('src/CMakeLists.txt', patch_cmake)

# types.h: modern MinGW compatibility and PSS_STYLE.
def patch_types(s):
    s = re.sub(r'(?m)^\s*#\s*define\s+stat\s+_stat\s*$', '/* modern MinGW: stat mapping not needed */', s)
    s = re.sub(r'(?m)^\s*#\s*define\s+R_OK\s+2\s*$', '/* modern MinGW already defines R_OK */', s)
    s = s.replace('#elif defined(MSVC)', '#elif defined(_WIN32) || defined(WIN32) || defined(MSVC)', 1)
    return s
rw('src/types.h', patch_types)

# emufile: ftruncate -> Windows CRT.
def patch_emufile(s):
    if '#include <io.h>' not in s:
        m = re.search(r'(?m)^#include[^\n]*$', s)
        if m:
            s = s[:m.end()] + '\n#ifdef _WIN32\n#include <io.h>\n#endif' + s[m.end():]
    s = s.replace('ftruncate(fileno(fp),length)', '_chsize_s(_fileno(fp), (__int64)length)')
    s = s.replace('ftruncate(fileno(fp), length)', '_chsize_s(_fileno(fp), (__int64)length)')
    return s
rw('src/emufile.cpp', patch_emufile)

# input.cpp: old Win32 debugger/input helper headers are only for __WIN_DRIVER__.
def patch_input(s):
    s = s.replace('#ifdef WIN32\n#include "drivers/win/debugger.h"', '#ifdef __WIN_DRIVER__\n#include "drivers/win/debugger.h"')
    s = s.replace('#if defined(WIN32)\n#include "drivers/win/debugger.h"', '#if defined(__WIN_DRIVER__)\n#include "drivers/win/debugger.h"')
    return s
rw('src/input.cpp', patch_input)

# lua-engine: private Win32/IUP internals only for classic win driver.
def patch_lua(s):
    s = s.replace('#ifdef WIN32\n#include <lstate.h>', '#ifdef __WIN_DRIVER__\n#include <lstate.h>', 1)
    return s
rw('src/lua-engine.cpp', patch_lua)

# SDL2 header name modernization across source tree.
for p in src.rglob('*'):
    if p.suffix.lower() not in {'.h','.hpp','.c','.cc','.cpp','.cxx'}:
        continue
    s = p.read_text(encoding='utf-8', errors='ignore')
    n = s.replace('#include <SDL.h>', '#include <SDL2/SDL.h>').replace('#include "SDL.h"', '#include <SDL2/SDL.h>')
    if n != s:
        p.write_text(n, encoding='utf-8', newline='\n')
        print('SDL2 include:', p.relative_to(root))

# fceu.cpp native hooks.
def patch_fceu(s):
    if '#include "cgemu342.h"' not in s:
        incs = list(re.finditer(r'(?m)^#include[^\n]*\n', s))
        if not incs: raise SystemExit('fceu include block missing')
        at = incs[-1].end()
        s = s[:at] + '#include "cgemu342.h"\n' + s[at:]
    old = '''FCEUGI *FCEUI_LoadGame(const char *name, int OverwriteVidMode, bool silent)\n{\n\treturn FCEUI_LoadGameVirtual(name, OverwriteVidMode, silent);\n}'''
    new = '''FCEUGI *FCEUI_LoadGame(const char *name, int OverwriteVidMode, bool silent)\n{\n\tFCEUGI *gi = FCEUI_LoadGameVirtual(name, OverwriteVidMode, silent);\n\tif (gi) CGEMU342_OnRomLoaded(name);\n\treturn gi;\n}'''
    if old not in s: raise SystemExit('FCEUI_LoadGame wrapper not found')
    s = s.replace(old, new, 1)
    if 'CGEMU342_PollMailbox();' not in s:
        needle = 'FCEU_StateRecorderUpdate();'
        if needle not in s: raise SystemExit('frame insertion point missing')
        s = s.replace(needle, needle + '\n\tCGEMU342_PollMailbox();', 1)
    return s
rw('src/fceu.cpp', patch_fceu)

# Qt frontend: deferred load after emulation returns.
def patch_qt(s):
    if '#include "../../cgemu342.h"' not in s:
        incs = list(re.finditer(r'(?m)^#include[^\n]*\n', s))
        if not incs: raise SystemExit('Qt include block missing')
        at = incs[-1].end()
        s = s[:at] + '#include "../../cgemu342.h"\n' + s[at:]
    old = '\tFCEUI_Emulate(&gfx, &sound, &ssize, fskipc);\n\tFCEUD_Update(gfx, sound, ssize);'
    new = '\tFCEUI_Emulate(&gfx, &sound, &ssize, fskipc);\n\tCGEMU342_TryDeferredLoad();\n\tFCEUD_Update(gfx, sound, ssize);'
    if old not in s: raise SystemExit('Qt FCEUI_Emulate site missing')
    return s.replace(old, new, 1)
rw('src/drivers/Qt/fceuWrapper.cpp', patch_qt)

# Copy native implementation supplied beside this script.
helper = Path(__file__).resolve().parent
for name in ('cgemu342.cpp','cgemu342.h'):
    srcp = helper / name
    if not srcp.exists(): raise SystemExit(f'missing helper {name}')
    (src/name).write_text(srcp.read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
    print('installed:', name)

print('PATCH COMPLETE')
