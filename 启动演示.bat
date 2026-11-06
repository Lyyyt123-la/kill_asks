@echo off
chcp 65001 >nul
title AskData - Judge Launcher
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\judge_start.ps1"
pause
