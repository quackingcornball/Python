@echo off
title Cricket Score Tracker
echo Starting Cricket Score Tracker...
"C:\Users\arvin\AppData\Local\Programs\Python\Python312\python.exe" "%~dp0main.py"
if %errorlevel% neq 0 (
    echo.
    echo An error occurred while running the application.
    echo Make sure Python is installed at the specified path.
    pause
)
