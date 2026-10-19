@echo off
rem Fix Fusion hotkeys (Alt+C / Alt+V) for whoever runs it.
rem Only edits %APPDATA%\Blackmagic Design\Fusion\Profiles and keeps backups.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix_fusion_hotkeys.ps1"
echo.
pause
