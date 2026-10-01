from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()


def patch(path, old, new, label):
    p = root / path
    s = p.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n")
    if old not in s:
        if new in s:
            print(f"already patched: {label}")
            return
        raise SystemExit(f"compat patch marker not found: {label}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8", newline="\n")
    print(f"patched: {label}")


# The Qt driver is built on Windows, so modern MinGW defines WIN32 even though
# FCEUX's legacy Win32 UI driver is not in use.  Keep its headers out of the
# common input core; the Qt frontend supplies its own debugger/UI integration.
patch(
    "src/input.cpp",
    '#ifdef WIN32\n#include "drivers/win/main.h"',
    '#ifdef __WIN_DRIVER__\n#include "drivers/win/main.h"',
    "input.cpp legacy Win32 UI include block",
)

# FCEUX a62b868 predates stricter modern GCC preprocessing rules.  Expanding a
# macro call directly next to ## is rejected by GCC 16.  Use a two-stage CAT so
# the inner SBT(name, Color) expands before the R/G/B suffix is pasted.
patch(
    "src/drivers/win/debugger.h",
    '#define SBCLR(name, suf) SBT(name, Color)##suf',
    '#define CAT_I(a, b) a##b\n#define CAT(a, b) CAT_I(a, b)\n#define SBCLR(name, suf) CAT(SBT(name, Color), suf)',
    "debugger.h token concatenation",
)

print("MINGW COMPAT PATCH COMPLETE")
