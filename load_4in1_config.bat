@echo off
cd /d "%~dp0"

:: SEADISTAME TÄPSED ASUKOHAD
set "ASM_ARCHIVE=configs\4 in 1.7z"
set "IMG_ARCHIVE=images\4 in 1.7z"
set "SEVENZIP_EXE=C:\Program Files\7-Zip\7z.exe"
set "TARGET_DIR=images"

echo --- Konfiguratsiooni laadimine: 4 in 1 ---

:: 1. Kontrollime 7-Zipi
if not exist "%SEVENZIP_EXE%" (
    echo VIGA: 7z.exe ei leitud!
    pause
    exit /b
)

:: 2. Pakime koodifailid (.asm) peakausta
echo 1/2: Pakin lahti koodi...
if exist "%ASM_ARCHIVE%" (
    "%SEVENZIP_EXE%" e "%ASM_ARCHIVE%" *.asm -aoa -y > nul
)

:: 3. Pakime pildid (.png) OTSE images kataloogi
echo 2/2: Pakin lahti pildid arhiivist: "%IMG_ARCHIVE%"
if exist "%IMG_ARCHIVE%" (
    "%SEVENZIP_EXE%" e "%IMG_ARCHIVE%" *.png -o"%TARGET_DIR%" -aoa -y
) else (
    echo.
    echo VIGA: Ei leia faili "%IMG_ARCHIVE%"
    pause
    exit /b
)

:: 4. KUSTUTAME VANA PALETIFAILI
echo Puhastan vana paleti faili...
if exist sprites_palette.bin (
    del /f /q sprites_palette.bin
    echo Vana sprites_palette.bin kustutatud.
)

echo.
echo --- KONTROLL: Kas uued pildid on kohal? ---
dir "%TARGET_DIR%\*.png" /b
echo --------------------------------------------------

:: 5. Käivitame ehituse
if exist "images\menu_header.png" (
    echo Koik korras! Kaivitan build.bat...
    call build.bat
) else (
    echo VIGA: images\menu_header.png puudub!
    pause
)