#!/usr/bin/env python3
"""
Comprehensive Database Backup System for Labor Lookers Platform
Automated backup, restoration, and monitoring capabilities
"""

import os
import shutil
import sqlite3
import json
import gzip
import schedule
import time
from datetime import datetime, timedelta
from pathlib import Path
import threading
import hashlib

class DatabaseBackupManager:
    def __init__(self, db_path="instance/laborlooker.db", backup_dir="backups"):
        self.db_path = db_path
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different backup types
        self.daily_dir = self.backup_dir / "daily"
        self.weekly_dir = self.backup_dir / "weekly"
        self.monthly_dir = self.backup_dir / "monthly"
        self.emergency_dir = self.backup_dir / "emergency"
        
        for dir_path in [self.daily_dir, self.weekly_dir, self.monthly_dir, self.emergency_dir]:
            dir_path.mkdir(exist_ok=True)
            
        self.backup_log = self.backup_dir / "backup_log.json"
        self.config_file = self.backup_dir / "backup_config.json"
        
        # Initialize configuration
        self.setup_config()
        
    def setup_config(self):
        """Initialize backup configuration"""
        default_config = {
            "retention_policy": {
                "daily_backups": 7,      # Keep 7 daily backups
                "weekly_backups": 4,     # Keep 4 weekly backups
                "monthly_backups": 12,   # Keep 12 monthly backups
                "emergency_backups": 10  # Keep 10 emergency backups
            },
            "compression": True,
            "verify_backups": True,
            "backup_schedule": {
                "daily_time": "02:00",   # 2 AM daily
                "weekly_day": "sunday",  # Sunday weekly
                "monthly_day": 1         # 1st of month
            },
            "alert_on_failure": True,
            "max_backup_size_mb": 1000   # Alert if backup exceeds 1GB
        }
        
        if not self.config_file.exists():
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
                
        with open(self.config_file, 'r') as f:
            self.config = json.load(f)
            
    def get_database_info(self):
        """Get database statistics and health info"""
        if not os.path.exists(self.db_path):
            return None
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get database size
            db_size = os.path.getsize(self.db_path)
            
            # Get table count and row counts
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            table_info = {}
            total_rows = 0
            
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                row_count = cursor.fetchone()[0]
                table_info[table_name] = row_count
                total_rows += row_count
                
            # Get database integrity check
            cursor.execute("PRAGMA integrity_check;")
            integrity = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "size_bytes": db_size,
                "size_mb": round(db_size / (1024 * 1024), 2),
                "total_tables": len(tables),
                "total_rows": total_rows,
                "table_info": table_info,
                "integrity": integrity,
                "last_modified": datetime.fromtimestamp(os.path.getmtime(self.db_path)).isoformat()
            }
            
        except Exception as e:
            print(f"Error getting database info: {e}")
            return None
            
    def create_backup(self, backup_type="manual", description=""):
        """Create a database backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Determine backup directory based on type
            if backup_type == "daily":
                backup_dir = self.daily_dir
            elif backup_type == "weekly":
                backup_dir = self.weekly_dir
            elif backup_type == "monthly":
                backup_dir = self.monthly_dir
            elif backup_type == "emergency":
                backup_dir = self.emergency_dir
            else:
                backup_dir = self.backup_dir
                
            # Create backup filename
            backup_name = f"laborlooker_backup_{backup_type}_{timestamp}"
            backup_path = backup_dir / f"{backup_name}.db"
            
            # Get database info before backup
            db_info = self.get_database_info()
            
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"Database file not found: {self.db_path}")
                
            # Create backup using SQLite backup API for consistency
            source_conn = sqlite3.connect(self.db_path)
            backup_conn = sqlite3.connect(str(backup_path))
            
            # Perform backup
            source_conn.backup(backup_conn)
            
            source_conn.close()
            backup_conn.close()
            
            # Compress backup if enabled
            if self.config.get("compression", True):
                compressed_path = backup_dir / f"{backup_name}.db.gz"
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                        
                # Remove uncompressed file
                backup_path.unlink()
                backup_path = compressed_path
                
            # Calculate backup checksum
            backup_hash = self.calculate_file_hash(backup_path)
            
            # Verify backup if enabled
            verification_status = "skipped"
            if self.config.get("verify_backups", True):
                verification_status = self.verify_backup(backup_path)
                
            # Log backup
            backup_record = {
                "timestamp": datetime.now().isoformat(),
                "backup_type": backup_type,
                "backup_path": str(backup_path),
                "backup_size": backup_path.stat().st_size,
                "original_size": db_info["size_bytes"] if db_info else 0,
                "compression_ratio": round(backup_path.stat().st_size / (db_info["size_bytes"] if db_info and db_info["size_bytes"] > 0 else 1), 2),
                "checksum": backup_hash,
                "verification_status": verification_status,
                "database_info": db_info,
                "description": description
            }
            
            self.log_backup(backup_record)
            
            # Clean old backups based on retention policy
            self.cleanup_old_backups(backup_type)
            
            print(f"✅ Backup created successfully: {backup_path}")
            print(f"   Size: {backup_record['backup_size'] / (1024*1024):.2f} MB")
            print(f"   Compression: {backup_record['compression_ratio']:.2f}")
            print(f"   Verification: {verification_status}")
            
            return backup_record
            
        except Exception as e:
            error_msg = f"Backup failed: {str(e)}"
            print(f"❌ {error_msg}")
            
            # Log failure
            self.log_backup({
                "timestamp": datetime.now().isoformat(),
                "backup_type": backup_type,
                "status": "failed",
                "error": error_msg,
                "description": description
            })
            
            return None
            
    def calculate_file_hash(self, file_path):
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
        
    def verify_backup(self, backup_path):
        """Verify backup integrity"""
        try:
            # For compressed backups
            if backup_path.suffix == '.gz':
                with gzip.open(backup_path, 'rb') as f:
                    temp_path = backup_path.parent / "temp_verify.db"
                    with open(temp_path, 'wb') as temp_f:
                        shutil.copyfileobj(f, temp_f)
                    
                    # Test database connection and integrity
                    conn = sqlite3.connect(str(temp_path))
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA integrity_check;")
                    result = cursor.fetchone()[0]
                    conn.close()
                    
                    # Clean up temp file
                    temp_path.unlink()
                    
            else:
                # Test database connection and integrity
                conn = sqlite3.connect(str(backup_path))
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check;")
                result = cursor.fetchone()[0]
                conn.close()
                
            return "passed" if result == "ok" else f"failed: {result}"
            
        except Exception as e:
            return f"failed: {str(e)}"
            
    def log_backup(self, backup_record):
        """Log backup operation"""
        log_data = []
        
        if self.backup_log.exists():
            with open(self.backup_log, 'r') as f:
                log_data = json.load(f)
                
        log_data.append(backup_record)
        
        # Keep only last 1000 log entries
        if len(log_data) > 1000:
            log_data = log_data[-1000:]
            
        with open(self.backup_log, 'w') as f:
            json.dump(log_data, f, indent=2)
            
    def cleanup_old_backups(self, backup_type):
        """Clean up old backups based on retention policy"""
        retention = self.config["retention_policy"]
        
        if backup_type == "daily":
            self._cleanup_directory(self.daily_dir, retention["daily_backups"])
        elif backup_type == "weekly":
            self._cleanup_directory(self.weekly_dir, retention["weekly_backups"])
        elif backup_type == "monthly":
            self._cleanup_directory(self.monthly_dir, retention["monthly_backups"])
        elif backup_type == "emergency":
            self._cleanup_directory(self.emergency_dir, retention["emergency_backups"])
            
    def _cleanup_directory(self, directory, keep_count):
        """Remove old backup files, keeping only the specified count"""
        backup_files = sorted(directory.glob("*.db*"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        if len(backup_files) > keep_count:
            files_to_delete = backup_files[keep_count:]
            for file_path in files_to_delete:
                try:
                    file_path.unlink()
                    print(f"🗑️  Cleaned up old backup: {file_path.name}")
                except Exception as e:
                    print(f"❌ Failed to delete old backup {file_path}: {e}")
                    
    def restore_backup(self, backup_path, target_path=None):
        """Restore database from backup"""
        try:
            if target_path is None:
                target_path = self.db_path
                
            backup_path = Path(backup_path)
            
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
                
            # Create emergency backup of current database
            if os.path.exists(target_path):
                emergency_backup = self.create_backup("emergency", f"Pre-restore backup from {datetime.now()}")
                print(f"📦 Created emergency backup before restore")
                
            # Restore from backup
            if backup_path.suffix == '.gz':
                # Decompress and restore
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(target_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # Direct copy
                shutil.copy2(backup_path, target_path)
                
            # Verify restored database
            verification = self.verify_backup(Path(target_path))
            
            print(f"✅ Database restored from: {backup_path}")
            print(f"   Target: {target_path}")
            print(f"   Verification: {verification}")
            
            return True
            
        except Exception as e:
            print(f"❌ Restore failed: {str(e)}")
            return False
            
    def list_backups(self, backup_type=None):
        """List available backups"""
        backups = []
        
        directories = []
        if backup_type is None:
            directories = [self.daily_dir, self.weekly_dir, self.monthly_dir, self.emergency_dir]
        elif backup_type == "daily":
            directories = [self.daily_dir]
        elif backup_type == "weekly":
            directories = [self.weekly_dir]
        elif backup_type == "monthly":
            directories = [self.monthly_dir]
        elif backup_type == "emergency":
            directories = [self.emergency_dir]
            
        for directory in directories:
            for backup_file in sorted(directory.glob("*.db*"), key=lambda x: x.stat().st_mtime, reverse=True):
                file_stat = backup_file.stat()
                backups.append({
                    "path": str(backup_file),
                    "type": backup_file.parent.name,
                    "size_mb": round(file_stat.st_size / (1024*1024), 2),
                    "created": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    "name": backup_file.name
                })
                
        return backups
        
    def get_backup_status(self):
        """Get comprehensive backup system status"""
        db_info = self.get_database_info()
        backups = self.list_backups()
        
        # Calculate total backup size
        total_backup_size = sum(backup["size_mb"] for backup in backups)
        
        # Get last backup info
        recent_backups = sorted(backups, key=lambda x: x["created"], reverse=True)[:5]
        
        # Check for backup health issues
        health_issues = []
        
        if not backups:
            health_issues.append("No backups found")
        else:
            last_backup = recent_backups[0]
            last_backup_time = datetime.fromisoformat(last_backup["created"])
            if datetime.now() - last_backup_time > timedelta(days=2):
                health_issues.append("Last backup is older than 2 days")
                
        return {
            "database_info": db_info,
            "total_backups": len(backups),
            "total_backup_size_mb": round(total_backup_size, 2),
            "recent_backups": recent_backups,
            "backup_counts": {
                "daily": len([b for b in backups if b["type"] == "daily"]),
                "weekly": len([b for b in backups if b["type"] == "weekly"]),
                "monthly": len([b for b in backups if b["type"] == "monthly"]),
                "emergency": len([b for b in backups if b["type"] == "emergency"])
            },
            "health_issues": health_issues,
            "config": self.config
        }
        
    def setup_automated_backups(self):
        """Setup automated backup scheduling"""
        print("🕐 Setting up automated backup schedule...")
        
        # Daily backup at 2 AM
        schedule.every().day.at(self.config["backup_schedule"]["daily_time"]).do(
            self.create_backup, "daily", "Automated daily backup"
        )
        
        # Weekly backup on Sunday
        schedule.every().sunday.at(self.config["backup_schedule"]["daily_time"]).do(
            self.create_backup, "weekly", "Automated weekly backup"
        )
        
        # Monthly backup on 1st of month
        schedule.every().day.at(self.config["backup_schedule"]["daily_time"]).do(
            self._check_monthly_backup
        )
        
        print("✅ Automated backup schedule configured")
        
    def _check_monthly_backup(self):
        """Check if monthly backup is needed"""
        if datetime.now().day == self.config["backup_schedule"]["monthly_day"]:
            self.create_backup("monthly", "Automated monthly backup")
            
    def run_backup_scheduler(self):
        """Run the backup scheduler in background"""
        print("🚀 Starting backup scheduler...")
        
        def scheduler_loop():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        scheduler_thread.start()
        
        print("✅ Backup scheduler running in background")
        return scheduler_thread

def main():
    """Main backup management interface"""
    backup_manager = DatabaseBackupManager()
    
    print("🗄️  LABOR LOOKERS DATABASE BACKUP SYSTEM")
    print("=" * 50)
    
    while True:
        print("\n📋 Available Options:")
        print("1. Create Manual Backup")
        print("2. Create Emergency Backup")
        print("3. List All Backups")
        print("4. Restore from Backup")
        print("5. Show Backup Status")
        print("6. Start Automated Backup Scheduler")
        print("7. Test Database Connection")
        print("8. Exit")
        
        choice = input("\nSelect option (1-8): ").strip()
        
        if choice == "1":
            description = input("Enter backup description (optional): ").strip()
            backup_manager.create_backup("manual", description)
            
        elif choice == "2":
            description = input("Enter emergency backup description: ").strip()
            backup_manager.create_backup("emergency", description)
            
        elif choice == "3":
            backups = backup_manager.list_backups()
            print(f"\n📦 Found {len(backups)} backups:")
            for backup in backups:
                print(f"   {backup['name']} ({backup['type']}) - {backup['size_mb']} MB - {backup['created']}")
                
        elif choice == "4":
            backups = backup_manager.list_backups()
            if not backups:
                print("❌ No backups available for restore")
                continue
                
            print("\n📦 Available backups:")
            for i, backup in enumerate(backups):
                print(f"   {i+1}. {backup['name']} ({backup['type']}) - {backup['created']}")
                
            try:
                backup_index = int(input("Select backup number: ")) - 1
                if 0 <= backup_index < len(backups):
                    confirm = input(f"Restore from {backups[backup_index]['name']}? (yes/no): ")
                    if confirm.lower() == 'yes':
                        backup_manager.restore_backup(backups[backup_index]['path'])
                else:
                    print("❌ Invalid backup selection")
            except ValueError:
                print("❌ Invalid input")
                
        elif choice == "5":
            status = backup_manager.get_backup_status()
            print(f"\n📊 BACKUP SYSTEM STATUS:")
            print(f"   Database Size: {status['database_info']['size_mb'] if status['database_info'] else 'Unknown'} MB")
            print(f"   Total Backups: {status['total_backups']}")
            print(f"   Total Backup Size: {status['total_backup_size_mb']} MB")
            print(f"   Daily Backups: {status['backup_counts']['daily']}")
            print(f"   Weekly Backups: {status['backup_counts']['weekly']}")
            print(f"   Monthly Backups: {status['backup_counts']['monthly']}")
            print(f"   Emergency Backups: {status['backup_counts']['emergency']}")
            
            if status['health_issues']:
                print(f"⚠️  Health Issues:")
                for issue in status['health_issues']:
                    print(f"     - {issue}")
            else:
                print("✅ Backup system healthy")
                
        elif choice == "6":
            backup_manager.setup_automated_backups()
            scheduler_thread = backup_manager.run_backup_scheduler()
            print("🔄 Automated backups running. Press Enter to stop...")
            input()
            print("🛑 Stopping automated backups...")
            
        elif choice == "7":
            db_info = backup_manager.get_database_info()
            if db_info:
                print(f"✅ Database connection successful")
                print(f"   Tables: {db_info['total_tables']}")
                print(f"   Total Rows: {db_info['total_rows']}")
                print(f"   Integrity: {db_info['integrity']}")
            else:
                print("❌ Database connection failed")
                
        elif choice == "8":
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main()