@echo off
rem Double-click to start the VideoToText demo. Runs start-demo.ps1 without
rem needing to change PowerShell's execution policy.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-demo.ps1" %*
if errorlevel 1 pause
