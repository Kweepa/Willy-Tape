@echo off
\app\acme\acme -o rope_test.prg --vicelabels rope_test.lbl rope_test.asm
if errorlevel 1 exit /b 1
\app\vice3.10\bin\c1541 -format "rope,01" d64 rope_test.d64
if errorlevel 1 exit /b 1
\app\vice3.10\bin\c1541 rope_test.d64 -write rope_test.prg rope
if errorlevel 1 exit /b 1
\app\vice3.10\bin\xvic -pal +basicload -autostart rope_test.d64
