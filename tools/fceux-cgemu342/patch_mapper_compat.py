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
        raise SystemExit(f"mapper compat marker not found: {label}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8", newline="\n")
    print(f"patched: {label}")


# In the pinned FCEUX, GenMMC3Close() is intentionally static inside mmc3.cpp,
# while newer FCEUmm exports it.  Preserve the close callback installed by
# GenMMC3_Init(), then chain to it from mapper 393's custom CHR-RAM cleanup.
p = root / "src/boards/393.cpp"
s = p.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n")

s = s.replace(
    "static uint32_t CHRRAMSIZE;",
    "static uint32_t CHRRAMSIZE;\nstatic void (*M393BaseClose)(void);",
    1,
)
s = s.replace(
    "static void M393lose(void) {\n\tGenMMC3Close();",
    "static void M393lose(void) {\n\tif (M393BaseClose) M393BaseClose();",
    1,
)
s = s.replace(
    "\tGenMMC3_Init(info, 1024, 512, 8, 0);",
    "\tGenMMC3_Init(info, 1024, 512, 8, 0);\n\tM393BaseClose = info->Close;",
    1,
)

if "GenMMC3Close();" in s:
    raise SystemExit("mapper 393 still references inaccessible GenMMC3Close")
if "M393BaseClose = info->Close;" not in s:
    raise SystemExit("mapper 393 base close hook patch failed")
p.write_text(s, encoding="utf-8", newline="\n")
print("patched: mapper 393 close chaining")

print("MAPPER COMPAT PATCH COMPLETE")
