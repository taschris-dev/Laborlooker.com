# 🗄️ Labor Lookers Database Backup System

Complete backup solution for the Labor Lookers platform with automated scheduling, compression, verification, and restore capabilities.

## 📋 Quick Start

### Windows Users (Recommended)
```batch
# Create a manual backup
backup.bat manual

# Check backup status
backup.bat status

# List all backups
backup.bat list

# Interactive mode
backup.bat
```

### PowerShell Users (Advanced)
```powershell
# Create daily backup
.\backup_automation.ps1 daily

# Setup automated daily backups
.\backup_automation.ps1 schedule

# Status with quiet mode
.\backup_automation.ps1 status -Quiet
```

### Direct Python Access
```bash
# Create backup
python backup_simple.py create manual

# Interactive mode
python backup_simple.py
```

## 🔧 System Components

### 1. `backup_simple.py` - Core Backup Engine
- **Purpose**: Main backup/restore functionality
- **Features**: 
  - SQLite backup API for safe database copying
  - Compression (gzip) to save space
  - Integrity verification after each backup
  - SHA256 checksum validation
  - Automatic cleanup of old backups
  - Restore capabilities with emergency backup

### 2. `backup.bat` - Windows Automation
- **Purpose**: Easy Windows batch automation
- **Features**:
  - Simple command-line interface
  - Logging to `backup_log.txt`
  - Interactive menu mode
  - Error handling and validation

### 3. `backup_automation.ps1` - Advanced PowerShell
- **Purpose**: Enterprise-grade automation
- **Features**:
  - Windows Task Scheduler integration
  - Advanced logging with rotation
  - Prerequisites checking
  - Scheduled backup setup (daily at 2:00 AM)

## 📂 Backup Directory Structure

```
backups/
├── daily/          # Automated daily backups
├── manual/         # Manual user backups  
├── emergency/      # Pre-restore emergency backups
├── backup_log.txt  # Simple logging
└── backup_automation.log  # Advanced logging
```

## 🔄 Backup Types

### Daily Backups
- **When**: Automated daily (2:00 AM if scheduled)
- **Retention**: 7 days (configurable)
- **Purpose**: Regular data protection

### Manual Backups  
- **When**: On-demand by user
- **Retention**: 7 backups
- **Purpose**: Before major changes

### Emergency Backups
- **When**: Automatically before restore operations
- **Retention**: 7 backups  
- **Purpose**: Safety net for restores

## 🛠️ Setup Instructions

### 1. Basic Setup
```bash
# Ensure Python is installed
python --version

# Test backup system
python backup_simple.py status
```

### 2. Windows Automation Setup
```batch
# Test batch script
backup.bat help

# Create first backup
backup.bat manual
```

### 3. Advanced PowerShell Setup
```powershell
# Set execution policy (if needed)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Test PowerShell script
.\backup_automation.ps1 help

# Setup scheduled backups
.\backup_automation.ps1 schedule
```

## 📊 Monitoring & Verification

### Backup Status
```bash
# Quick status check
python backup_simple.py status

# Example output:
📊 BACKUP STATUS:
   Database: OK (15 tables, 1,247 total rows)
   Database Size: 2.34 MB
   Total Backups: 12
   Daily: 5
   Manual: 4
   Emergency: 3
   Total Backup Size: 8.2 MB
```

### Backup Verification
Each backup includes:
- **Integrity Check**: SQLite PRAGMA integrity_check
- **Table Count**: Verification of table structure
- **Row Count**: Data verification
- **Checksum**: SHA256 hash for corruption detection
- **Compression Ratio**: Space savings metric

## 🔧 Configuration Options

### Retention Policies
Edit `backup_simple.py`:
```python
def cleanup_old_backups(self, backup_type, keep_count=7):
    # Change keep_count to adjust retention
```

### Compression Settings
```python
def create_backup(self, backup_type="manual", compress=True):
    # Set compress=False to disable compression
```

### Backup Schedule
For PowerShell automation:
```powershell
# Edit backup_automation.ps1
$Trigger = New-ScheduledTaskTrigger -Daily -At "02:00"
# Change time as needed
```

## 🚨 Disaster Recovery

### Restore Process
```bash
# List available backups
python backup_simple.py list

# Interactive restore (recommended)
python backup_simple.py
# Choose option 5 (Restore Backup)

# Manual restore
# Emergency backup is created automatically
```

### Emergency Procedures
1. **Database Corruption**:
   ```bash
   python backup_simple.py create emergency
   # Find most recent good backup
   python backup_simple.py list
   # Restore via interactive mode
   ```

2. **Accidental Data Loss**:
   ```bash
   # Immediate emergency backup
   backup.bat emergency
   
   # Review recent backups
   backup.bat list
   
   # Restore from appropriate backup
   ```

## 📈 Best Practices

### 1. Regular Monitoring
- Check backup status weekly
- Verify recent backups exist
- Monitor log files for errors

### 2. Test Restores
```bash
# Monthly restore test (to test database)
cp instance/laborlooker.db instance/laborlooker_test.db
python backup_simple.py
# Restore to test database and verify
```

### 3. Storage Management
- Monitor backup directory size
- Archive old backups if needed
- Consider external backup storage

### 4. Automation Setup
```powershell
# Recommended: Setup scheduled backups
.\backup_automation.ps1 schedule

# Verify scheduled task
Get-ScheduledTask -TaskName "LaborLookersBackup"
```

## 🔍 Troubleshooting

### Common Issues

#### "Database file not found"
```bash
# Check database path
ls instance/laborlooker.db

# Initialize database if needed
python main.py
```

#### "Python not found"
```bash
# Windows: Add Python to PATH
# Or use full path
C:\Python39\python.exe backup_simple.py status
```

#### "Permission denied"
```bash
# Ensure write permissions
chmod 755 backups/
```

#### PowerShell execution policy
```powershell
# For current user only
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Log Analysis
```bash
# Check backup logs
type backup_log.txt
type backup_automation.log

# Look for:
# - SUCCESS messages
# - ERROR entries
# - Backup file sizes
# - Verification results
```

## 📋 Backup Checklist

### Daily Operations
- [ ] Backup system running (if scheduled)
- [ ] No errors in logs
- [ ] Database size reasonable

### Weekly Review
- [ ] Check backup status
- [ ] Verify recent backups exist
- [ ] Review log files
- [ ] Test backup creation

### Monthly Tasks
- [ ] Test restore procedure
- [ ] Review retention policies
- [ ] Archive old backups
- [ ] Update backup scripts if needed

## 🚀 Production Deployment

### Pre-Deployment
1. Test backup system thoroughly
2. Setup scheduled backups
3. Verify restore procedures
4. Document backup locations

### Monitoring
```bash
# Add to server monitoring
python backup_simple.py status
# Exit code 0 = success, 1 = failure

# Log monitoring for errors
grep -i error backup_automation.log
```

### Security
- Secure backup directory permissions
- Consider encrypting backups for sensitive data
- Regular offsite backup copies
- Access control for restore operations

## 📞 Support

For backup system issues:
1. Check log files first
2. Verify database integrity
3. Test with manual backup
4. Review error messages
5. Check file permissions

**Emergency Contact**: Backup system is designed to be self-recovering with multiple safety nets and detailed logging for quick issue resolution.

---

**Status**: ✅ Production Ready  
**Last Updated**: October 2024  
**Version**: 1.0.0