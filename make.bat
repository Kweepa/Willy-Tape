@echo off
rem JSW-Tape: single PRG build (16K expanded cassette port)

echo [1/3] Catalogue...
python tools\export_spriteframes_asm.py
python tools\mkcatalogue.py --rooms rooms --out catalogue.bin --map catalogue.map
if errorlevel 1 exit /b 1

echo [2/3] Assembling jsw.prg...
\app\acme\acme -o jsw.prg --vicelabels jsw.lbl jsw.asm
if errorlevel 1 exit /b 1
AcmeLabelSorter jsw.lbl jsws.lbl

echo [3/3] ZP map...
python tools\zpmap.py --asm
if errorlevel 1 exit /b 1

python tools\memmap.py --tape
if errorlevel 1 exit /b 1

echo.
echo Build OK: jsw.prg loads at $1201 (catalogue embedded at CatalogueImage)

\app\vice3.10\bin\xvic -pal +basicload -autostart jsw.prg
