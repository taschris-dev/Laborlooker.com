#!/usr/bin/env python3
"""
Simple Database Backup Script for Labor Lookers Platform
Quick and reliable backup solution
"""

import os
import shutil
import sqlite3
import json
import gzip
from datetime import datetime
from pathlib import Path
import hashlib

class SimpleBackupManager:
    def __init__(self, db_path="instance/laborlooker.db"):
        self.db_path = db_path
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # Create backup subdirectories
        (self.backup_dir / "daily").mkdir(exist_ok=True)
        (self.backup_dir / "manual").mkdir(exist_ok=True)
        (self.backup_dir / "emergency").mkdir(exist_ok=True)
        
    def create_backup(self, backup_type="manual", compress=True):
        """Create a simple database backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"laborlooker_backup_{backup_type}_{timestamp}.db"
            backup_path = self.backup_dir / backup_type / backup_name
            
            print(f"🔄 Creating {backup_type} backup...")
            
            # Check if source database exists
            if not os.path.exists(self.db_path):
                print(f"❌ Database file not found: {self.db_path}")
                return False
                
            # Get database size
            db_size = os.path.getsize(self.db_path)
            print(f"📊 Database size: {db_size / (1024*1024):.2f} MB")
            
            # Create backup using SQLite backup API
            source_conn = sqlite3.connect(self.db_path)
            backup_conn = sqlite3.connect(str(backup_path))
            
            # Perform backup
            source_conn.backup(backup_conn)
            source_conn.close()
            backup_conn.close()
            
            # Compress if requested
            if compress:
                compressed_path = backup_path.with_suffix('.db.gz')
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                        
                backup_path.unlink()  # Remove uncompressed file
                backup_path = compressed_path
                
            # Calculate file hash for verification
            file_hash = self.calculate_hash(backup_path)
            
            # Get final backup size
            backup_size = backup_path.stat().st_size
            compression_ratio = backup_size / db_size if db_size > 0 else 1
            
            # Create backup info file
            info_file = backup_path.with_suffix('.info.json')
            backup_info = {
                "created": datetime.now().isoformat(),
                "source_db": str(self.db_path),
                "backup_type": backup_type,
                "original_size": db_size,
                "backup_size": backup_size,
                "compression_ratio": round(compression_ratio, 2),
                "compressed": compress,
                "checksum": file_hash,
                "verification": self.verify_backup(backup_path)
            }
            
            with open(info_file, 'w') as f:
                json.dump(backup_info, f, indent=2)
                
            print("✅ Backup created successfully!")
            print(f"   Location: {backup_path}")
            print(f"   Size: {backup_size / (1024*1024):.2f} MB")
            print(f"   Compression: {compression_ratio:.1%}")
            print(f"   Verification: {backup_info['verification']}")
            
            # Clean up old backups
            self.cleanup_old_backups(backup_type)
            
            return True
            
        except Exception as e:
            print(f"❌ Backup failed: {str(e)}")
            return False
            
    def calculate_hash(self, file_path):
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()[:16]  # First 16 chars for brevity
        
    def verify_backup(self, backup_path):
        """Verify backup can be opened and is intact"""
        try:
            if backup_path.suffix == '.gz':
                # For compressed backups, decompress temporarily
                temp_path = backup_path.with_suffix('.temp.db')
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(temp_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Test the decompressed file
                conn = sqlite3.connect(str(temp_path))
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                cursor.execute("PRAGMA integrity_check;")
                integrity = cursor.fetchone()[0]
                conn.close()
                
                # Clean up temp file
                temp_path.unlink()
                
            else:
                # Test uncompressed backup directly
                conn = sqlite3.connect(str(backup_path))
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                cursor.execute("PRAGMA integrity_check;")
                integrity = cursor.fetchone()[0]
                conn.close()
                
            return f"OK ({len(tables)} tables)" if integrity == "ok" else f"ERROR: {integrity}"
            
        except Exception as e:
            return f"FAILED: {str(e)}"
            
    def cleanup_old_backups(self, backup_type, keep_count=7):
        """Remove old backups, keeping only the most recent ones"""
        backup_dir = self.backup_dir / backup_type
        backup_files = sorted(backup_dir.glob("*.db*"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Keep info files with their backups
        backup_pairs = []
        for backup_file in backup_files:
            if not backup_file.name.endswith('.info.json'):
                info_file = backup_file.with_suffix('.info.json')
                backup_pairs.append((backup_file, info_file))
                
        if len(backup_pairs) > keep_count:
            files_to_delete = backup_pairs[keep_count:]
            for backup_file, info_file in files_to_delete:
                try:
                    backup_file.unlink()
                    if info_file.exists():
                        info_file.unlink()
                    print(f"🗑️  Removed old backup: {backup_file.name}")
                except Exception as e:
                    print(f"⚠️  Could not remove {backup_file.name}: {e}")
                    
    def list_backups(self):
        """List all available backups"""
        backups = []
        
        for backup_type in ['daily', 'manual', 'emergency']:
            backup_dir = self.backup_dir / backup_type
            if not backup_dir.exists():
                continue
                
            for backup_file in sorted(backup_dir.glob("*.db*"), key=lambda x: x.stat().st_mtime, reverse=True):
                if backup_file.name.endswith('.info.json'):
                    continue
                    
                info_file = backup_file.with_suffix('.info.json')
                info = {}
                
                if info_file.exists():
                    try:
                        with open(info_file, 'r') as f:
                            info = json.load(f)
                    except Exception:
                        pass
                        
                backups.append({
                    'path': str(backup_file),
                    'type': backup_type,
                    'name': backup_file.name,
                    'size_mb': round(backup_file.stat().st_size / (1024*1024), 2),
                    'created': info.get('created', 'Unknown'),
                    'verification': info.get('verification', 'Unknown'),
                    'checksum': info.get('checksum', 'Unknown')
                })
                
        return backups
        
    def restore_backup(self, backup_path, target_path=None):
        """Restore database from backup"""
        try:
            if target_path is None:
                target_path = self.db_path
                
            backup_path = Path(backup_path)
            
            print(f"🔄 Restoring from: {backup_path.name}")
            
            # Create emergency backup first
            if os.path.exists(target_path):
                print("📦 Creating emergency backup of current database...")
                self.create_backup("emergency", compress=True)
                
            # Restore from backup
            if backup_path.suffix == '.gz':
                print("📂 Decompressing backup...")
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(target_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                print("📂 Copying backup...")
                shutil.copy2(backup_path, target_path)
                
            # Verify restored database
            verification = self.verify_database(target_path)
            
            print(f"✅ Database restored successfully!")
            print(f"   Verification: {verification}")
            
            return True
            
        except Exception as e:
            print(f"❌ Restore failed: {str(e)}")
            return False
            
    def verify_database(self, db_path):
        """Verify database integrity"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            # Check integrity
            cursor.execute("PRAGMA integrity_check;")
            integrity = cursor.fetchone()[0]
            
            # Count total rows
            total_rows = 0
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table[0]};")
                    total_rows += cursor.fetchone()[0]
                except:
                    pass
                    
            conn.close()
            
            return f"OK ({len(tables)} tables, {total_rows} total rows)" if integrity == "ok" else f"ERROR: {integrity}"
            
        except Exception as e:
            return f"FAILED: {str(e)}"
            
    def get_backup_status(self):
        """Get backup system status"""
        backups = self.list_backups()
        
        if not os.path.exists(self.db_path):
            db_status = "Database file not found"
            db_size = 0
        else:
            db_status = self.verify_database(self.db_path)
            db_size = os.path.getsize(self.db_path)
            
        backup_counts = {}
        total_backup_size = 0
        
        for backup_type in ['daily', 'manual', 'emergency']:
            type_backups = [b for b in backups if b['type'] == backup_type]
            backup_counts[backup_type] = len(type_backups)
            total_backup_size += sum(b['size_mb'] for b in type_backups)
            
        return {
            'database_status': db_status,
            'database_size_mb': round(db_size / (1024*1024), 2),
            'total_backups': len(backups),
            'backup_counts': backup_counts,
            'total_backup_size_mb': round(total_backup_size, 2),
            'recent_backups': backups[:5]
        }

def main():
    """Command-line interface for backup management"""
    backup_manager = SimpleBackupManager()
    
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "create":
            backup_type = sys.argv[2] if len(sys.argv) > 2 else "manual"
            success = backup_manager.create_backup(backup_type)
            sys.exit(0 if success else 1)
            
        elif command == "list":
            backups = backup_manager.list_backups()
            print(f"📦 Found {len(backups)} backups:")
            for backup in backups:
                print(f"   {backup['name']} ({backup['type']}) - {backup['size_mb']} MB - {backup['created']}")
            sys.exit(0)
            
        elif command == "status":
            status = backup_manager.get_backup_status()
            print("📊 BACKUP STATUS:")
            print(f"   Database: {status['database_status']}")
            print(f"   Database Size: {status['database_size_mb']} MB")
            print(f"   Total Backups: {status['total_backups']}")
            print(f"   Daily: {status['backup_counts']['daily']}")
            print(f"   Manual: {status['backup_counts']['manual']}")
            print(f"   Emergency: {status['backup_counts']['emergency']}")
            print(f"   Total Backup Size: {status['total_backup_size_mb']} MB")
            sys.exit(0)
            
        elif command == "help":
            print("📋 BACKUP COMMANDS:")
            print("   python backup_simple.py create [daily|manual|emergency]")
            print("   python backup_simple.py list")
            print("   python backup_simple.py status")
            print("   python backup_simple.py help")
            sys.exit(0)
            
    # Interactive mode
    print("🗄️  LABOR LOOKERS DATABASE BACKUP")
    print("=" * 40)
    
    while True:
        print("\n📋 Options:")
        print("1. Create Manual Backup")
        print("2. Create Emergency Backup") 
        print("3. List Backups")
        print("4. Show Status")
        print("5. Restore Backup")
        print("6. Exit")
        
        choice = input("\nChoice (1-6): ").strip()
        
        if choice == "1":
            backup_manager.create_backup("manual")
        elif choice == "2":
            backup_manager.create_backup("emergency")
        elif choice == "3":
            backups = backup_manager.list_backups()
            print(f"\n📦 Found {len(backups)} backups:")
            for i, backup in enumerate(backups, 1):
                print(f"   {i}. {backup['name']} ({backup['type']}) - {backup['size_mb']} MB")
                print(f"      Created: {backup['created']}")
                print(f"      Status: {backup['verification']}")
        elif choice == "4":
            status = backup_manager.get_backup_status()
            print(f"\n📊 BACKUP STATUS:")
            print(f"   Database: {status['database_status']}")
            print(f"   Database Size: {status['database_size_mb']} MB")
            print(f"   Total Backups: {status['total_backups']}")
            print(f"   Backup Size: {status['total_backup_size_mb']} MB")
        elif choice == "5":
            backups = backup_manager.list_backups()
            if not backups:
                print("❌ No backups available")
                continue
            print(f"\n📦 Available backups:")
            for i, backup in enumerate(backups, 1):
                print(f"   {i}. {backup['name']} - {backup['created']}")
            try:
                selection = int(input("Select backup number: ")) - 1
                if 0 <= selection < len(backups):
                    confirm = input(f"Restore from {backups[selection]['name']}? (yes/no): ")
                    if confirm.lower() == 'yes':
                        backup_manager.restore_backup(backups[selection]['path'])
            except (ValueError, IndexError):
                print("❌ Invalid selection")
        elif choice == "6":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()