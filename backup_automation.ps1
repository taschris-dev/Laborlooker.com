# Labor Lookers Database Backup PowerShell Script
# Advanced automation with logging and error handling

param(
    [Parameter(Position=0)]
    [ValidateSet("daily", "manual", "emergency", "status", "list", "schedule", "help")]
    [string]$Action = "interactive",
    
    [switch]$Quiet,
    [switch]$Compress = $true
)

# Configuration
$BackupScript = "backup_simple.py"
$LogFile = "backup_automation.log"
$MaxLogSize = 10MB

# Function to write logs
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "[$Timestamp] [$Level] $Message"
    
    # Write to console if not quiet
    if (-not $Quiet) {
        switch ($Level) {
            "ERROR" { Write-Host $LogEntry -ForegroundColor Red }
            "WARN"  { Write-Host $LogEntry -ForegroundColor Yellow }
            "SUCCESS" { Write-Host $LogEntry -ForegroundColor Green }
            default { Write-Host $LogEntry }
        }
    }
    
    # Write to log file
    try {
        # Rotate log if too large
        if (Test-Path $LogFile) {
            $LogSize = (Get-Item $LogFile).Length
            if ($LogSize -gt $MaxLogSize) {
                $BackupLog = $LogFile + ".old"
                Move-Item $LogFile $BackupLog -Force
            }
        }
        
        Add-Content -Path $LogFile -Value $LogEntry
    }
    catch {
        Write-Host "Warning: Could not write to log file: $_" -ForegroundColor Yellow
    }
}

# Function to check prerequisites
function Test-Prerequisites {
    Write-Log "Checking prerequisites..."
    
    # Check Python
    try {
        $PythonVersion = python --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Log "Python is not installed or not in PATH" "ERROR"
            return $false
        }
        Write-Log "Found $PythonVersion"
    }
    catch {
        Write-Log "Error checking Python: $_" "ERROR"
        return $false
    }
    
    # Check backup script
    if (-not (Test-Path $BackupScript)) {
        Write-Log "Backup script not found: $BackupScript" "ERROR"
        return $false
    }
    Write-Log "Backup script found: $BackupScript"
    
    # Check database
    if (-not (Test-Path "instance/laborlooker.db")) {
        Write-Log "Database file not found: instance/laborlooker.db" "WARN"
    } else {
        $DbSize = (Get-Item "instance/laborlooker.db").Length / 1MB
        Write-Log "Database found (${DbSize:F2} MB)"
    }
    
    # Create backup directories
    $BackupDirs = @("backups", "backups/daily", "backups/manual", "backups/emergency")
    foreach ($Dir in $BackupDirs) {
        if (-not (Test-Path $Dir)) {
            New-Item -ItemType Directory -Path $Dir -Force | Out-Null
            Write-Log "Created directory: $Dir"
        }
    }
    
    return $true
}

# Function to run backup
function Invoke-Backup {
    param([string]$BackupType)
    
    Write-Log "Starting $BackupType backup..."
    
    try {
        $Process = Start-Process -FilePath "python" -ArgumentList "$BackupScript", "create", $BackupType -Wait -PassThru -NoNewWindow -RedirectStandardOutput "backup_output.tmp" -RedirectStandardError "backup_error.tmp"
        
        # Read output
        $Output = Get-Content "backup_output.tmp" -ErrorAction SilentlyContinue
        $ErrorOutput = Get-Content "backup_error.tmp" -ErrorAction SilentlyContinue
        
        # Clean up temp files
        Remove-Item "backup_output.tmp", "backup_error.tmp" -ErrorAction SilentlyContinue
        
        if ($Process.ExitCode -eq 0) {
            Write-Log "$BackupType backup completed successfully" "SUCCESS"
            if ($Output) {
                foreach ($Line in $Output) {
                    Write-Log "  $Line"
                }
            }
            return $true
        } else {
            Write-Log "$BackupType backup failed (Exit code: $($Process.ExitCode))" "ERROR"
            if ($ErrorOutput) {
                foreach ($Line in $ErrorOutput) {
                    Write-Log "  ERROR: $Line" "ERROR"
                }
            }
            return $false
        }
    }
    catch {
        Write-Log "Error running backup: $_" "ERROR"
        return $false
    }
}

# Function to show status
function Show-Status {
    Write-Log "Getting backup status..."
    
    try {
        $Output = python $BackupScript status 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n📊 BACKUP STATUS:" -ForegroundColor Cyan
            $Output | ForEach-Object { Write-Host "   $_" }
        } else {
            Write-Log "Error getting status: $Output" "ERROR"
        }
    }
    catch {
        Write-Log "Error getting status: $_" "ERROR"
    }
}

# Function to list backups
function Show-Backups {
    Write-Log "Listing backups..."
    
    try {
        $Output = python $BackupScript list 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n📦 AVAILABLE BACKUPS:" -ForegroundColor Cyan
            $Output | ForEach-Object { Write-Host "   $_" }
        } else {
            Write-Log "Error listing backups: $Output" "ERROR"
        }
    }
    catch {
        Write-Log "Error listing backups: $_" "ERROR"
    }
}

# Function to setup scheduled backup
function Set-ScheduledBackup {
    Write-Log "Setting up scheduled backup..."
    
    $TaskName = "LaborLookersBackup"
    $ScriptPath = $PSScriptRoot + "\backup_automation.ps1"
    
    try {
        # Check if task exists
        $ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        
        if ($ExistingTask) {
            Write-Log "Scheduled task already exists: $TaskName" "WARN"
            $Update = Read-Host "Update existing task? (y/n)"
            if ($Update -ne "y") {
                return
            }
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        }
        
        # Create new task
        $Action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File `"$ScriptPath`" daily -Quiet"
        $Trigger = New-ScheduledTaskTrigger -Daily -At "02:00"
        $Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U
        $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
        
        Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description "Daily backup for Labor Lookers database"
        
        Write-Log "Scheduled task created: $TaskName (daily at 2:00 AM)" "SUCCESS"
    }
    catch {
        Write-Log "Error setting up scheduled task: $_" "ERROR"
    }
}

# Function to show help
function Show-Help {
    Write-Host "`n🗄️  LABOR LOOKERS BACKUP AUTOMATION" -ForegroundColor Cyan
    Write-Host "=" * 50
    Write-Host "`nUSAGE:" -ForegroundColor Yellow
    Write-Host "  backup_automation.ps1 [action] [options]"
    Write-Host "`nACTIONS:" -ForegroundColor Yellow
    Write-Host "  daily      - Create daily backup"
    Write-Host "  manual     - Create manual backup"
    Write-Host "  emergency  - Create emergency backup"
    Write-Host "  status     - Show backup status"
    Write-Host "  list       - List all backups"
    Write-Host "  schedule   - Setup automated daily backups"
    Write-Host "  help       - Show this help"
    Write-Host "`nOPTIONS:" -ForegroundColor Yellow
    Write-Host "  -Quiet     - Suppress console output"
    Write-Host "  -Compress  - Compress backups (default: true)"
    Write-Host "`nEXAMPLES:" -ForegroundColor Green
    Write-Host "  backup_automation.ps1 daily"
    Write-Host "  backup_automation.ps1 manual -Quiet"
    Write-Host "  backup_automation.ps1 schedule"
    Write-Host ""
}

# Main execution
function Main {
    Write-Log "Labor Lookers Backup Automation Started"
    
    # Check prerequisites
    if (-not (Test-Prerequisites)) {
        Write-Log "Prerequisites check failed" "ERROR"
        exit 1
    }
    
    # Handle actions
    switch ($Action) {
        "daily" {
            $Success = Invoke-Backup "daily"
            exit $(if ($Success) { 0 } else { 1 })
        }
        "manual" {
            $Success = Invoke-Backup "manual"
            exit $(if ($Success) { 0 } else { 1 })
        }
        "emergency" {
            $Success = Invoke-Backup "emergency"
            exit $(if ($Success) { 0 } else { 1 })
        }
        "status" {
            Show-Status
        }
        "list" {
            Show-Backups
        }
        "schedule" {
            Set-ScheduledBackup
        }
        "help" {
            Show-Help
        }
        "interactive" {
            # Interactive mode
            Write-Host "`n🗄️  LABOR LOOKERS BACKUP AUTOMATION" -ForegroundColor Cyan
            Write-Host "=" * 50
            
            do {
                Write-Host "`n📋 Choose an option:" -ForegroundColor Yellow
                Write-Host "1. Create Daily Backup"
                Write-Host "2. Create Manual Backup"
                Write-Host "3. Create Emergency Backup"
                Write-Host "4. Show Backup Status"
                Write-Host "5. List All Backups"
                Write-Host "6. Setup Scheduled Backups"
                Write-Host "7. Show Help"
                Write-Host "8. Exit"
                
                $Choice = Read-Host "`nEnter choice (1-8)"
                
                switch ($Choice) {
                    "1" { Invoke-Backup "daily" }
                    "2" { Invoke-Backup "manual" }
                    "3" { Invoke-Backup "emergency" }
                    "4" { Show-Status }
                    "5" { Show-Backups }
                    "6" { Set-ScheduledBackup }
                    "7" { Show-Help }
                    "8" { break }
                    default { Write-Host "❌ Invalid choice. Please enter 1-8." -ForegroundColor Red }
                }
                
                if ($Choice -ne "8") {
                    Write-Host "`nPress any key to continue..." -ForegroundColor Gray
                    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
                }
            } while ($Choice -ne "8")
        }
    }
    
    Write-Log "Backup automation completed"
}

# Run main function
Main