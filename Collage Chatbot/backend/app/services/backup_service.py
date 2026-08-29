"""
Backup and Disaster Recovery Service for AIT AI Assistant
Handles database backups, knowledge data backups, document backups, and restore procedures
"""

import os
import shutil
import tarfile
import datetime
import hashlib
import json
from typing import Optional, List, Dict, Tuple
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
import logging
from backend.app.config import settings

logger = logging.getLogger(__name__)


class BackupService:
    """
    Comprehensive backup and disaster recovery service
    """
    
    def __init__(self, backup_dir: str = None):
        self.backup_dir = backup_dir or os.getenv("BACKUP_DIR", "./backups")
        self.backup_retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
        self._ensure_backup_directory()
    
    def _ensure_backup_directory(self):
        """Ensure backup directory exists"""
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        subdirs = ['database', 'knowledge', 'documents', 'uploads', 'system']
        for subdir in subdirs:
            Path(self.backup_dir, subdir).mkdir(parents=True, exist_ok=True)
    
    def create_database_backup(self, db_session: Session) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Create database backup
        
        Returns:
            (success, error_message, backup_path)
        """
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"database_backup_{timestamp}.sql"
            backup_path = os.path.join(self.backup_dir, 'database', backup_filename)
            
            # For SQLite, just copy the database file
            if hasattr(settings, 'DATABASE_URL') and 'sqlite' in settings.DATABASE_URL:
                db_path = settings.DATABASE_URL.replace('sqlite:///', '')
                if os.path.exists(db_path):
                    shutil.copy2(db_path, backup_path)
                    logger.info(f"Database backup created: {backup_path}")
                    return True, None, backup_path
                else:
                    return False, f"Database file not found: {db_path}", None
            
            # For PostgreSQL, use pg_dump
            elif hasattr(settings, 'DATABASE_URL') and 'postgresql' in settings.DATABASE_URL:
                import subprocess
                env = os.environ.copy()
                env['PGPASSWORD'] = os.getenv('POSTGRES_PASSWORD', '')
                
                # Extract connection details
                db_url = settings.DATABASE_URL.replace('postgresql://', '')
                user, password, host, port, database = self._parse_postgres_url(db_url)
                
                cmd = [
                    'pg_dump',
                    f'--host={host}',
                    f'--port={port}',
                    f'--username={user}',
                    f'--dbname={database}',
                    '--no-password',
                    '--format=plain',
                    '--file=' + backup_path
                ]
                
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info(f"Database backup created: {backup_path}")
                    return True, None, backup_path
                else:
                    return False, f"pg_dump failed: {result.stderr}", None
            
            else:
                return False, "Unsupported database type", None
                
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False, str(e), None
    
    def _parse_postgres_url(self, db_url: str) -> Tuple[str, str, str, str, str]:
        """Parse PostgreSQL connection URL"""
        # Simple parsing - in production use proper URL parser
        parts = db_url.split('@')
        user_pass = parts[0].split('//')[1]
        host_port_db = parts[1].split('/')
        
        user, password = user_pass.split(':')
        host_port = host_port_db[0].split(':')
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else '5432'
        database = host_port_db[1]
        
        return user, password, host, port, database
    
    def create_knowledge_backup(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Create knowledge data backup (documents, chunks, conflicts)
        
        Returns:
            (success, error_message, backup_path)
        """
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"knowledge_backup_{timestamp}.tar.gz"
            backup_path = os.path.join(self.backup_dir, 'knowledge', backup_filename)
            
            # Create knowledge directory backup
            knowledge_dirs = [
                'rag/documents',
                'rag/chunks', 
                'rag/knowledge_base',
                'database/seed'
            ]
            
            with tarfile.open(backup_path, "w:gz") as tar:
                for dir_path in knowledge_dirs:
                    if os.path.exists(dir_path):
                        tar.add(dir_path, arcname=os.path.basename(dir_path))
            
            logger.info(f"Knowledge backup created: {backup_path}")
            return True, None, backup_path
            
        except Exception as e:
            logger.error(f"Knowledge backup failed: {e}")
            return False, str(e), None
    
    def create_uploads_backup(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Create uploaded files backup
        
        Returns:
            (success, error_message, backup_path)
        """
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"uploads_backup_{timestamp}.tar.gz"
            backup_path = os.path.join(self.backup_dir, 'uploads', backup_filename)
            
            upload_dirs = [
                'uploads',
                'media',
                'audio_cache'
            ]
            
            with tarfile.open(backup_path, "w:gz") as tar:
                for dir_path in upload_dirs:
                    if os.path.exists(dir_path):
                        tar.add(dir_path, arcname=os.path.basename(dir_path))
            
            logger.info(f"Uploads backup created: {backup_path}")
            return True, None, backup_path
            
        except Exception as e:
            logger.error(f"Uploads backup failed: {e}")
            return False, str(e), None
    
    def create_system_backup(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Create system configuration backup
        
        Returns:
            (success, error_message, backup_path)
        """
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"system_backup_{timestamp}.tar.gz"
            backup_path = os.path.join(self.backup_dir, 'system', backup_filename)
            
            system_files = [
                '.env',
                'backend/app/config.py',
                'docker-compose.yml',
                'backend/requirements.txt',
                'frontend/package.json'
            ]
            
            with tarfile.open(backup_path, "w:gz") as tar:
                for file_path in system_files:
                    if os.path.exists(file_path):
                        tar.add(file_path, arcname=os.path.basename(file_path))
            
            logger.info(f"System backup created: {backup_path}")
            return True, None, backup_path
            
        except Exception as e:
            logger.error(f"System backup failed: {e}")
            return False, str(e), None
    
    def create_full_backup(self, db_session: Session) -> Tuple[bool, Optional[str], Dict[str, str]]:
        """
        Create complete system backup
        
        Returns:
            (success, error_message, backup_info)
        """
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_info = {
                'timestamp': timestamp,
                'backup_id': hashlib.md5(timestamp.encode()).hexdigest()[:8],
                'components': {}
            }
            
            # Database backup
            db_success, db_error, db_path = self.create_database_backup(db_session)
            backup_info['components']['database'] = {
                'success': db_success,
                'path': db_path,
                'error': db_error
            }
            
            # Knowledge backup
            knowledge_success, knowledge_error, knowledge_path = self.create_knowledge_backup()
            backup_info['components']['knowledge'] = {
                'success': knowledge_success,
                'path': knowledge_path,
                'error': knowledge_error
            }
            
            # Uploads backup
            uploads_success, uploads_error, uploads_path = self.create_uploads_backup()
            backup_info['components']['uploads'] = {
                'success': uploads_success,
                'path': uploads_path,
                'error': uploads_error
            }
            
            # System backup
            system_success, system_error, system_path = self.create_system_backup()
            backup_info['components']['system'] = {
                'success': system_success,
                'path': system_path,
                'error': system_error
            }
            
            # Save backup metadata
            metadata_path = os.path.join(self.backup_dir, f"backup_metadata_{timestamp}.json")
            with open(metadata_path, 'w') as f:
                json.dump(backup_info, f, indent=2)
            
            # Check if all components succeeded
            all_success = all(
                comp['success'] for comp in backup_info['components'].values()
            )
            
            if all_success:
                logger.info(f"Full backup completed successfully: {backup_info['backup_id']}")
                return True, None, backup_info
            else:
                logger.warning(f"Full backup completed with partial failures: {backup_info['backup_id']}")
                return True, "Some backup components failed", backup_info
                
        except Exception as e:
            logger.error(f"Full backup failed: {e}")
            return False, str(e), {}
    
    def restore_database(self, backup_path: str) -> Tuple[bool, Optional[str]]:
        """
        Restore database from backup
        
        Returns:
            (success, error_message)
        """
        try:
            if not os.path.exists(backup_path):
                return False, f"Backup file not found: {backup_path}"
            
            # For SQLite, restore by copying
            if hasattr(settings, 'DATABASE_URL') and 'sqlite' in settings.DATABASE_URL:
                db_path = settings.DATABASE_URL.replace('sqlite:///', '')
                shutil.copy2(backup_path, db_path)
                logger.info(f"Database restored from: {backup_path}")
                return True, None
            
            # For PostgreSQL, use psql
            elif hasattr(settings, 'DATABASE_URL') and 'postgresql' in settings.DATABASE_URL:
                import subprocess
                env = os.environ.copy()
                env['PGPASSWORD'] = os.getenv('POSTGRES_PASSWORD', '')
                
                db_url = settings.DATABASE_URL.replace('postgresql://', '')
                user, password, host, port, database = self._parse_postgres_url(db_url)
                
                cmd = [
                    'psql',
                    f'--host={host}',
                    f'--port={port}',
                    f'--username={user}',
                    f'--dbname={database}',
                    '--no-password',
                    '--file=' + backup_path
                ]
                
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info(f"Database restored from: {backup_path}")
                    return True, None
                else:
                    return False, f"psql failed: {result.stderr}"
            
            else:
                return False, "Unsupported database type"
                
        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False, str(e)
    
    def cleanup_old_backups(self) -> Tuple[int, List[str]]:
        """
        Remove backups older than retention period
        
        Returns:
            (files_deleted, deleted_files)
        """
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=self.backup_retention_days)
            deleted_files = []
            
            for root, dirs, files in os.walk(self.backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_date = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_date < cutoff_date:
                        os.remove(file_path)
                        deleted_files.append(file_path)
                        logger.info(f"Deleted old backup: {file_path}")
            
            return len(deleted_files), deleted_files
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return 0, []
    
    def get_backup_status(self) -> Dict[str, any]:
        """
        Get current backup status
        
        Returns:
            backup_status dictionary
        """
        backup_info = {
            'backup_directory': self.backup_dir,
            'retention_days': self.backup_retention_days,
            'total_backups': 0,
            'total_size_mb': 0,
            'last_backup': None,
            'backups_by_type': {
                'database': 0,
                'knowledge': 0,
                'uploads': 0,
                'system': 0
            }
        }
        
        try:
            for root, dirs, files in os.walk(self.backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    backup_info['total_backups'] += 1
                    backup_info['total_size_mb'] += file_size / (1024 * 1024)
                    
                    # Categorize by type
                    if 'database' in root:
                        backup_info['backups_by_type']['database'] += 1
                    elif 'knowledge' in root:
                        backup_info['backups_by_type']['knowledge'] += 1
                    elif 'uploads' in root:
                        backup_info['backups_by_type']['uploads'] += 1
                    elif 'system' in root:
                        backup_info['backups_by_type']['system'] += 1
                    
                    # Track last backup
                    file_date = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    if backup_info['last_backup'] is None or file_date > backup_info['last_backup']:
                        backup_info['last_backup'] = file_date
            
            backup_info['total_size_mb'] = round(backup_info['total_size_mb'], 2)
            
        except Exception as e:
            logger.error(f"Failed to get backup status: {e}")
        
        return backup_info