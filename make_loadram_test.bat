@echo off
python tools\mkloadram_test.py --payload-only
if errorlevel 1 exit /b 1
\app\acme\acme -o loadram_test.prg --vicelabels loadram_test.lbl loadram_test.asm
if errorlevel 1 exit /b 1
python tools\mkloadram_test.py
if errorlevel 1 exit /b 1
\app\vice3.10\bin\xvic -pal +basicload -autostart loadram_test.d64
