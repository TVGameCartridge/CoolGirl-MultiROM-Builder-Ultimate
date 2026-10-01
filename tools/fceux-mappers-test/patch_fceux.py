from pathlib import Path
import sys
import urllib.request

root = Path(sys.argv[1]).resolve()
boards = root / 'src' / 'boards'

urls = {
    'gn26.cpp': 'https://raw.githubusercontent.com/Yhc-Studio/FCEUX-2.6.6-Yhc/main/src/boards/gn26.cpp',
    '393.cpp': 'https://raw.githubusercontent.com/Yhc-Studio/FCEUX-2.6.6-Yhc/main/src/boards/393.cpp',
    '395.cpp': 'https://raw.githubusercontent.com/Yhc-Studio/FCEUX-2.6.6-Yhc/main/src/boards/395.cpp',
    '359.cpp': 'https://raw.githubusercontent.com/Yhc-Studio/FCEUX-2.6.6-Yhc/main/src/boards/359.cpp',
    '90.cpp': 'https://raw.githubusercontent.com/Yhc-Studio/FCEUX-2.6.6-Yhc/main/src/boards/90.cpp',
}
for name, url in urls.items():
    print('Downloading', name)
    urllib.request.urlretrieve(url, boards / name)

mmc3_path = boards / 'mmc3.cpp'
mmc3 = mmc3_path.read_text(encoding='utf-8', errors='surrogateescape')
if 'void Mapper315_Init(CartInfo *info)' not in mmc3:
    mmc3 += r'''

// NES 2.0 Mapper 315 - 830134C / 820733C family
static void M315PW(uint32 A, uint8 V) {
    int outerBank = (EXPREGS[0] >> 1) & 3;
    if (outerBank == 3)
        syncPRG_GNROM_67(0x02, 0x0F, outerBank << 4);
    else
        syncPRG(0x0F, outerBank << 4);
}

static void M315CW(uint32 A, uint8 V) {
    syncCHR_ROM(0xFF, ((EXPREGS[0] & 0x08) ? 0x040 : 0x000) |
                      ((EXPREGS[0] & 0x02) ? 0x080 : 0x000) |
                      ((EXPREGS[0] & 0x01) ? 0x100 : 0x000));
}

static DECLFW(M315Write) {
    EXPREGS[0] = V;
    FixMMC3PRG(MMC3_cmd);
    FixMMC3CHR(MMC3_cmd);
}

static void M315_Reset(void) {
    EXPREGS[0] = 0;
    MMC3RegReset();
}

static void M315_Power(void) {
    M315_Reset();
    GenMMC3Power();
    SetWriteHandler(0x6000, 0x7FFF, M315Write);
}

void Mapper315_Init(CartInfo *info) {
    GenMMC3_Init(info, 128, 128, 8, info->battery);
    pwrap = M315PW;
    cwrap = M315CW;
    info->Power = M315_Power;
    info->Reset = M315_Reset;
    AddExState(EXPREGS, 1, 0, "EXPR");
}
'''
    mmc3_path.write_text(mmc3, encoding='utf-8', errors='surrogateescape')

ines_h_path = root / 'src' / 'ines.h'
ines_h = ines_h_path.read_text(encoding='utf-8', errors='surrogateescape')
if 'void Mapper315_Init(CartInfo *);' not in ines_h:
    anchor = 'void Mapper255_Init(CartInfo *);'
    if anchor not in ines_h:
        raise RuntimeError('ines.h anchor not found')
    decl = '''\nvoid Mapper315_Init(CartInfo *);\nvoid BMCGN26_Init(CartInfo *);\nvoid Mapper358_Init(CartInfo *);\nvoid Mapper393_Init(CartInfo *);\nvoid Mapper395_Init(CartInfo *);\nvoid Mapper359_Init(CartInfo *);\nvoid Mapper540_Init(CartInfo *);\n'''
    ines_h = ines_h.replace(anchor, anchor + decl, 1)
    ines_h_path.write_text(ines_h, encoding='utf-8', errors='surrogateescape')

ines_cpp_path = root / 'src' / 'ines.cpp'
ines_cpp = ines_cpp_path.read_text(encoding='utf-8', errors='surrogateescape')
if 'YOKO / Master Fighter VI' not in ines_cpp:
    anchor = '//-------- Mappers 256-511 is the Supplementary Multilingual Plane ----------'
    if anchor not in ines_cpp:
        raise RuntimeError('ines.cpp mapper-table anchor not found')
    entries = '''\t{"YOKO / Master Fighter VI", 264, UNLYOKO_Init},\n\t{"411120-C / 811120-C", 287, BMC411120C_Init},\n\t{"830134C / 820733C", 315, Mapper315_Init},\n\t{"BMC-GN-26", 344, BMCGN26_Init},\n\t{"JYASIC multicart", 358, Mapper358_Init},\n\t{"BMC 8-in-1 G002", 393, Mapper393_Init},\n\t{"Realtec 8210 / SPC003", 395, Mapper395_Init},\n\t{"UNL-82112C / EJ4003", 540, Mapper540_Init},\n\n'''
    ines_cpp = ines_cpp.replace(anchor, entries + anchor, 1)
    ines_cpp_path.write_text(ines_cpp, encoding='utf-8', errors='surrogateescape')

cmake_path = root / 'src' / 'CMakeLists.txt'
cmake = cmake_path.read_text(encoding='utf-8', errors='surrogateescape')
anchor = '\t${CMAKE_CURRENT_SOURCE_DIR}/boards/354.cpp'
for name in ('359.cpp', '393.cpp', '395.cpp', 'gn26.cpp'):
    line = '\t${CMAKE_CURRENT_SOURCE_DIR}/boards/' + name
    if line not in cmake:
        if anchor not in cmake:
            raise RuntimeError('CMake board-list anchor not found')
        cmake = cmake.replace(anchor, anchor + '\n' + line, 1)
cmake_path.write_text(cmake, encoding='utf-8', errors='surrogateescape')

print('FCEUX mapper patch applied: 45(existing), 264, 287, 315, 344, 358, 393, 395, 540')
