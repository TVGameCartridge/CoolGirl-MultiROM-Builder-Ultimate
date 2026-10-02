from pathlib import Path
import shutil, sys

root = Path(sys.argv[1]).resolve()
here = Path(__file__).resolve().parent
mapper_dir = root / "Core/NES/Mappers/Unlicensed"
mapper_dir.mkdir(parents=True, exist_ok=True)

files = [
    "Mapper315.h", "CoolGirl342.h", "Mapper344.h", "Mapper358.h",
    "Mapper393.h", "Mapper395.h", "Mapper540.h"
]
for name in files:
    shutil.copy2(here / "mappers" / name, mapper_dir / name)

p = root / "Core/NES/MapperFactory.cpp"
s = p.read_text(encoding="utf-8-sig").replace("\r\n", "\n")

include_marker = '#include "NES/Mappers/Unlicensed/Yoko.h"\n'
includes = ''.join(f'#include "NES/Mappers/Unlicensed/{name}"\n' for name in files)
if includes not in s:
    if include_marker not in s:
        raise SystemExit("MapperFactory include marker not found")
    s = s.replace(include_marker, include_marker + includes, 1)

replacements = {
    "\t\tcase 315: break; //830134C": "\t\tcase 315: return new Mapper315(); //830134C",
    "\t\tcase 342: break; //COOLGIRL": "\t\tcase 342: return new CoolGirl342(); //COOLGIRL",
    "\t\tcase 344: break; //GN26": "\t\tcase 344: return new Mapper344(); //GN26",
}
for old, new in replacements.items():
    if old in s:
        s = s.replace(old, new, 1)
    elif new not in s:
        raise SystemExit(f"MapperFactory marker missing: {old}")

block_old = "\t\tcase 350: break; //891227\n\n\t\tcase 366: return new BmcGn45();"
block_new = "\t\tcase 350: break; //891227\n\t\tcase 358: return new Mapper358();\n\t\tcase 393: return new Mapper393();\n\t\tcase 395: return new Mapper395();\n\n\t\tcase 366: return new BmcGn45();"
if block_old in s:
    s = s.replace(block_old, block_new, 1)
elif "case 358: return new Mapper358();" not in s:
    raise SystemExit("MapperFactory 350/366 marker missing")

block_old = "\t\tcase 530: return new Ax5705();\n\t\t\n\t\tcase 552: return new TaitoX1017();"
block_new = "\t\tcase 530: return new Ax5705();\n\t\tcase 540: return new Mapper540();\n\t\t\n\t\tcase 552: return new TaitoX1017();"
if block_old in s:
    s = s.replace(block_old, block_new, 1)
elif "case 540: return new Mapper540();" not in s:
    raise SystemExit("MapperFactory 530/552 marker missing")

p.write_text(s, encoding="utf-8", newline="\n")
print("MesenCE mapper patch complete:", ", ".join(files))
