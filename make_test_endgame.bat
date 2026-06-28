@echo off
rem Endgame test build: Maria vanishes after 2 pickups (r35 hook only).
rem Main jsw.prg and pickup_got are unchanged; only master_bed_hook threshold differs.

set ENDGAME_ITEMS=2

echo [1/4] Assembling resident jsw.prg...
\app\acme\acme -o jsw.prg --vicelabels jsw.lbl jsw.asm
if errorlevel 1 exit /b 1
AcmeLabelSorter jsw.lbl jsws.lbl

echo [2/4] ZP map...
python tools\zpmap.py --asm
if errorlevel 1 exit /b 1

echo [3/4] Building room PRGs (--endgame-items-required %ENDGAME_ITEMS%)...
python tools\mkroom.py --all rooms rooms\out --endgame-items-required %ENDGAME_ITEMS%

echo [4/4] Building disk image...
python tools\mkdisk.py --out jsw.d64 --prg jsw.prg --rooms rooms/out
if errorlevel 1 exit /b 1

python tools\mkroom.py --status rooms
python tools\memmap.py --slack
if errorlevel 1 exit /b 1
echo endgame threshold=%ENDGAME_ITEMS% (r35 hook only; pickup_got uses full room count)

\app\vice3.10\bin\xvic -pal +basicload -autostart jsw.d64
