@echo off
rem JSW-Tape: single PRG build (16K expanded cassette port)

echo [1/3] Catalogue...
python tools\export_spriteframes_asm.py
python tools\export_font_asm.py --rooms rooms
python tools\mkcatalogue.py --rooms rooms --out catalogue.bin --map catalogue.map
if errorlevel 1 exit /b 1

echo [2/3] Assembling jsw.prg...
for /f %%i in ('python tools\mkroom.py --count-items rooms') do set ENDGAME_ITEMS=%%i
\app\acme\acme -o jsw.prg --vicelabels jsw.lbl -DENDGAME_ITEMS_REQUIRED=%ENDGAME_ITEMS% jsw.asm
if errorlevel 1 exit /b 1
AcmeLabelSorter jsw.lbl jsws.lbl
python tools\lbloverlap.py jsws.lbl
if errorlevel 1 exit /b 1

echo [3/3] ZP map...
python tools\zpmap.py --asm
if errorlevel 1 exit /b 1

python tools\memmap.py --tape
if errorlevel 1 exit /b 1

echo.
echo Build OK: jsw.prg loads at $1201 (catalogue embedded at CatalogueImage)

\app\vice3.10\bin\xvic -pal +basicload -autostart jsw.prg
