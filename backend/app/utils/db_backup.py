"""
Database Backup Utility

Provides automatic backup functionality to prevent data loss.
Critical for legal docketing systems where data must never be lost.
"""
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Maximum number of backups to keep
MAX_BACKUPS = 10


def get_backup_dir() -> Path:
    """Get the backup directory, creating it if necessary."""
    backend_dir = Path(__file__).parent.parent.parent.absolute()
    backup_dir = backend_dir / "backups"
    backup_dir.mkdir(exist_ok=True)
    return backup_dir


def backup_sqlite_database(db_path: str, reason: str = "manual") -> str:
    """
    Create a backup of the SQLite database.

    Args:
        db_path: Path to the SQLite database file
        reason: Reason for backup (for logging and filename)

    Returns:
        Path to the backup file, or None if backup failed
    """
    try:
        # Extract just the path from SQLite URL
        if db_path.startswith("sqlite:///"):
            db_file = db_path.replace("sqlite:///", "")
        else:
            db_file = db_path

        if not os.path.exists(db_file):
            logger.warning(f"Database file not found: {db_file}")
            return None

        # Create backup filename with timestamp
        backup_dir = get_backup_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_name = Path(db_file).stem
        backup_name = f"{db_name}_{timestamp}_{reason}.db"
        backup_path = backup_dir / backup_name

        # Copy database file
        shutil.copy2(db_file, backup_path)
        logger.info(f"Database backed up to: {backup_path}")

        # Cleanup old backups
        cleanup_old_backups(backup_dir, db_name)

        return str(backup_path)

    except Exception as e:
        logger.error(f"Failed to backup database: {e}")
        return None


def cleanup_old_backups(backup_dir: Path, db_name: str):
    """
    Remove old backups, keeping only the most recent MAX_BACKUPS.
    """
    try:
        # Find all backups for this database
        backups = sorted(
            backup_dir.glob(f"{db_name}_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        # Remove old backups
        for old_backup in backups[MAX_BACKUPS:]:
            old_backup.unlink()
            logger.info(f"Removed old backup: {old_backup}")

    except Exception as e:
        logger.warning(f"Failed to cleanup old backups: {e}")


def restore_from_backup(backup_path: str, target_path: str) -> bool:
    """
    Restore database from a backup file.

    Args:
        backup_path: Path to the backup file
        target_path: Path where to restore the database

    Returns:
        True if restoration was successful
    """
    try:
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return False

        # Create a backup of current database before restoring
        if os.path.exists(target_path):
            backup_sqlite_database(target_path, reason="pre_restore")

        # Restore from backup
        shutil.copy2(backup_path, target_path)
        logger.info(f"Database restored from: {backup_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to restore database: {e}")
        return False


def list_backups() -> list:
    """
    List all available database backups.

    Returns:
        List of backup file information dictionaries
    """
    backup_dir = get_backup_dir()
    backups = []

    for backup_file in sorted(backup_dir.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = backup_file.stat()
        backups.append({
            "filename": backup_file.name,
            "path": str(backup_file),
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })

    return backups


def auto_backup_on_startup(db_url: str):
    """
    Create an automatic backup when the application starts.
    Called from main.py startup event.
    """
    if "sqlite" in db_url.lower():
        logger.info("Creating startup backup of SQLite database...")
        backup_path = backup_sqlite_database(db_url, reason="startup")
        if backup_path:
            logger.info(f"Startup backup created: {backup_path}")
        return backup_path
    else:
        logger.info("Non-SQLite database - backup handled by database service")
        return None
