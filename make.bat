@echo off
rem Build order: resident jsw.prg (jsw.lbl) -> room PRGs (ACME bake via mkroom) -> disk

echo [1/4] Assembling resident jsw.prg...
\app\acme\acme -o jsw.prg --vicelabels jsw.lbl jsw.asm
if errorlevel 1 exit /b 1
AcmeLabelSorter jsw.lbl jsws.lbl

echo [2/4] ZP map...
python tools\zpmap.py --asm
if errorlevel 1 exit /b 1

echo [3/4] Building room PRGs (bake/*.asm via mkroom, needs jsw.lbl for ScanKeyRow)...
python tools\mkroom.py --all rooms rooms\out

echo [4/4] Building disk image...
python tools\mkdisk.py --out jsw.d64 --prg jsw.prg --rooms rooms/out
if errorlevel 1 exit /b 1

python tools\mkroom.py --status rooms
python tools\memmap.py --slack
if errorlevel 1 exit /b 1
for /f %%i in ('python tools\mkroom.py --count-items rooms') do set PICKUP_COUNT=%%i
echo pickup count=%PICKUP_COUNT% (r35 hook baked via mkroom --all)

\app\vice3.10\bin\xvic -pal +basicload -autostart jsw.d64
