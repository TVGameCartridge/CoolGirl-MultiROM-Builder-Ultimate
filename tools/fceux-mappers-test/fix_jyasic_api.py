from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
p = root / 'src' / 'boards' / '90.cpp'
s = p.read_text(encoding='utf-8', errors='surrogateescape')
old = 'static void trapPPUAddressChange(uint32 A)'
new = 'static void trapPPUAddressChange(uint32 A, unsigned int)'
if old not in s and new not in s:
    raise RuntimeError('JYASIC PPU hook signature anchor not found')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8', errors='surrogateescape')
print('Adapted JYASIC GamePPUHook callback to FCEUX 2.7 two-argument API')
