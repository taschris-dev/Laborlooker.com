@echo off
REM Labor Lookers Database Backup Automation Script
REM For Windows environments

echo 🗄️  LABOR LOOKERS BACKUP AUTOMATION
echo ================================

REM Set backup directory
set BACKUP_DIR=backups
set LOG_FILE=backup_log.txt

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

REM Create backup directories
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
if not exist "%BACKUP_DIR%\daily" mkdir "%BACKUP_DIR%\daily"
if not exist "%BACKUP_DIR%\manual" mkdir "%BACKUP_DIR%\manual"
if not exist "%BACKUP_DIR%\emergency" mkdir "%BACKUP_DIR%\emergency"

REM Get current date and time for logging
for /f "tokens=1-5 delims=/ " %%a in ('date /t') do set CURRENT_DATE=%%c-%%a-%%b
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set CURRENT_TIME=%%a:%%b

echo [%CURRENT_DATE% %CURRENT_TIME%] Starting backup automation... >> %LOG_FILE%

REM Check if backup script exists
if not exist backup_simple.py (
    echo ❌ backup_simple.py not found
    echo Please ensure the backup script is in the current directory
    echo [%CURRENT_DATE% %CURRENT_TIME%] ERROR: backup_simple.py not found >> %LOG_FILE%
    pause
    exit /b 1
)

REM Check command line arguments
if "%1"=="" goto :interactive
if "%1"=="daily" goto :daily_backup
if "%1"=="manual" goto :manual_backup
if "%1"=="emergency" goto :emergency_backup
if "%1"=="status" goto :show_status
if "%1"=="list" goto :list_backups
if "%1"=="help" goto :show_help

goto :show_help

:daily_backup
echo 📅 Creating daily backup...
python backup_simple.py create daily
if errorlevel 1 (
    echo ❌ Daily backup failed
    echo [%CURRENT_DATE% %CURRENT_TIME%] ERROR: Daily backup failed >> %LOG_FILE%
) else (
    echo ✅ Daily backup completed
    echo [%CURRENT_DATE% %CURRENT_TIME%] SUCCESS: Daily backup completed >> %LOG_FILE%
)
goto :end

:manual_backup
echo 📦 Creating manual backup...
python backup_simple.py create manual
if errorlevel 1 (
    echo ❌ Manual backup failed
    echo [%CURRENT_DATE% %CURRENT_TIME%] ERROR: Manual backup failed >> %LOG_FILE%
) else (
    echo ✅ Manual backup completed
    echo [%CURRENT_DATE% %CURRENT_TIME%] SUCCESS: Manual backup completed >> %LOG_FILE%
)
goto :end

:emergency_backup
echo 🚨 Creating emergency backup...
python backup_simple.py create emergency
if errorlevel 1 (
    echo ❌ Emergency backup failed
    echo [%CURRENT_DATE% %CURRENT_TIME%] ERROR: Emergency backup failed >> %LOG_FILE%
) else (
    echo ✅ Emergency backup completed
    echo [%CURRENT_DATE% %CURRENT_TIME%] SUCCESS: Emergency backup completed >> %LOG_FILE%
)
goto :end

:show_status
echo 📊 Backup Status:
python backup_simple.py status
goto :end

:list_backups
echo 📋 Available Backups:
python backup_simple.py list
goto :end

:show_help
echo.
echo 📋 USAGE:
echo   backup.bat daily      - Create daily backup
echo   backup.bat manual     - Create manual backup  
echo   backup.bat emergency  - Create emergency backup
echo   backup.bat status     - Show backup status
echo   backup.bat list       - List all backups
echo   backup.bat help       - Show this help
echo   backup.bat            - Interactive mode
echo.
goto :end

:interactive
echo.
echo 🔄 INTERACTIVE BACKUP MODE
echo Choose an option:
echo.
echo 1. Create Daily Backup
echo 2. Create Manual Backup
echo 3. Create Emergency Backup
echo 4. Show Backup Status
echo 5. List All Backups
echo 6. Exit
echo.

set /p CHOICE="Enter choice (1-6): "

if "%CHOICE%"=="1" goto :daily_backup
if "%CHOICE%"=="2" goto :manual_backup
if "%CHOICE%"=="3" goto :emergency_backup
if "%CHOICE%"=="4" goto :show_status
if "%CHOICE%"=="5" goto :list_backups
if "%CHOICE%"=="6" goto :end

echo ❌ Invalid choice. Please enter 1-6.
goto :interactive

:end
echo.
echo 📝 Check backup_log.txt for detailed logs
echo 👋 Backup automation complete
if "%1"=="" pause