#!/usr/bin/env python3
"""
Database Utilities for WriteBot

Common database operations and maintenance tasks.

Usage:
    python db_utils.py backup                    # Backup database
    python db_utils.py restore <backup_file>     # Restore from backup
    python db_utils.py stats                     # Show database statistics
    python db_utils.py check                     # Check data integrity
    python db_utils.py vacuum                    # Optimize database
    python db_utils.py export <table>            # Export table to JSON
"""

import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text, inspect


class DatabaseUtils:
    """Database utility functions"""

    def __init__(self):
        self.db_path = self._get_db_path()
        self.backup_dir = Path(__file__).parent / 'backups'
        self.backup_dir.mkdir(exist_ok=True)

    def _get_db_path(self):
        """Get the database file path from app config"""
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        if db_uri.startswith('sqlite:///'):
            db_file = db_uri.replace('sqlite:///', '')
            if not db_file.startswith('/'):
                # Relative path
                return Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / db_file
            return Path(db_file)
        else:
            raise ValueError("Only SQLite databases are supported for these utilities")

    def backup(self):
        """Create a backup of the database"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f'writebot_{timestamp}.db'

        print(f"\n→ Backing up database...")
        print(f"  Source: {self.db_path}")
        print(f"  Backup: {backup_file}")

        if not self.db_path.exists():
            print(f"✗ Error: Database file not found at {self.db_path}")
            return

        try:
            shutil.copy2(self.db_path, backup_file)
            file_size = backup_file.stat().st_size / 1024  # KB
            print(f"✓ Backup created successfully ({file_size:.2f} KB)")
            print(f"\nBackup location: {backup_file}")
        except Exception as e:
            print(f"✗ Error creating backup: {str(e)}")

    def restore(self, backup_file):
        """Restore database from backup"""
        backup_path = Path(backup_file)

        if not backup_path.exists():
            print(f"✗ Error: Backup file not found at {backup_path}")
            return

        print(f"\n→ Restoring database from backup...")
        print(f"  Backup: {backup_path}")
        print(f"  Target: {self.db_path}")

        confirm = input("\nThis will overwrite the current database. Type 'YES' to confirm: ")
        if confirm != 'YES':
            print("Aborted.")
            return

        try:
            # Create a safety backup first
            if self.db_path.exists():
                safety_backup = self.db_path.parent / f"{self.db_path.name}.before_restore"
                shutil.copy2(self.db_path, safety_backup)
                print(f"✓ Created safety backup: {safety_backup}")

            # Restore from backup
            shutil.copy2(backup_path, self.db_path)
            print(f"✓ Database restored successfully")
        except Exception as e:
            print(f"✗ Error restoring backup: {str(e)}")

    def stats(self):
        """Show database statistics"""
        print("\n" + "="*60)
        print("DATABASE STATISTICS")
        print("="*60)

        with app.app_context():
            try:
                # System statistics view
                result = db.session.execute(text("SELECT * FROM system_statistics")).fetchone()

                if result:
                    print("\nSystem Overview:")
                    print("-"*60)
                    print(f"  Total Users:              {result[0]}")
                    print(f"  Active Users:             {result[1]}")
                    print(f"  Admin Users:              {result[2]}")
                    print(f"  Template Presets:         {result[3]}")
                    print(f"  Page Size Presets:        {result[4]}")
                    print(f"  Character Collections:    {result[5]}")
                    print(f"  Character Overrides:      {result[6]}")
                    print(f"  All-time SVG Generations: {result[7]}")
                    print(f"  All-time Lines Generated: {result[8]}")

                # Database file info
                if self.db_path.exists():
                    file_size = self.db_path.stat().st_size / (1024 * 1024)  # MB
                    print(f"\nDatabase File:")
                    print("-"*60)
                    print(f"  Path:     {self.db_path}")
                    print(f"  Size:     {file_size:.2f} MB")

                # Table sizes
                inspector = inspect(db.engine)
                tables = inspector.get_table_names()

                print(f"\nTables ({len(tables)}):")
                print("-"*60)

                for table in sorted(tables):
                    result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    print(f"  {table:<40} {result:>10} rows")

            except Exception as e:
                print(f"✗ Error retrieving statistics: {str(e)}")
                import traceback
                traceback.print_exc()

        print("="*60 + "\n")

    def check(self):
        """Check data integrity"""
        print("\n" + "="*60)
        print("DATA INTEGRITY CHECK")
        print("="*60)

        with app.app_context():
            try:
                # Run integrity check view
                results = db.session.execute(text("SELECT * FROM data_integrity_checks")).fetchall()

                print("\nChecking data integrity...")
                print("-"*60)

                issues_found = False
                for row in results:
                    table_name = row[0]
                    total_records = row[1]
                    issue_count = sum(row[2:])

                    status = "✓ OK" if issue_count == 0 else f"✗ {issue_count} issues"
                    print(f"  {table_name:<30} {total_records:>8} rows   {status}")

                    if issue_count > 0:
                        issues_found = True

                # Check for orphaned records
                print("\nChecking foreign key integrity...")
                print("-"*60)

                # Check user_activities without valid users
                result = db.session.execute(text("""
                    SELECT COUNT(*) FROM user_activities
                    WHERE user_id NOT IN (SELECT id FROM users)
                """)).scalar()

                if result > 0:
                    print(f"  ✗ Found {result} orphaned user_activities")
                    issues_found = True
                else:
                    print("  ✓ user_activities: OK")

                # Check usage_statistics without valid users
                result = db.session.execute(text("""
                    SELECT COUNT(*) FROM usage_statistics
                    WHERE user_id NOT IN (SELECT id FROM users)
                """)).scalar()

                if result > 0:
                    print(f"  ✗ Found {result} orphaned usage_statistics")
                    issues_found = True
                else:
                    print("  ✓ usage_statistics: OK")

                if not issues_found:
                    print("\n✓ No integrity issues found")
                else:
                    print("\n⚠ Data integrity issues detected!")

            except Exception as e:
                print(f"✗ Error checking integrity: {str(e)}")
                import traceback
                traceback.print_exc()

        print("="*60 + "\n")

    def vacuum(self):
        """Optimize database (VACUUM)"""
        print("\n→ Optimizing database...")

        with app.app_context():
            try:
                # Get size before
                size_before = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0

                # Run VACUUM
                db.session.execute(text("VACUUM"))
                db.session.commit()

                # Get size after
                size_after = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0

                savings = size_before - size_after
                percent = (savings / size_before * 100) if size_before > 0 else 0

                print(f"✓ Database optimized")
                print(f"  Before: {size_before:.2f} MB")
                print(f"  After:  {size_after:.2f} MB")
                print(f"  Saved:  {savings:.2f} MB ({percent:.1f}%)")

            except Exception as e:
                print(f"✗ Error optimizing database: {str(e)}")

    def export_table(self, table_name):
        """Export table data to JSON"""
        output_file = self.backup_dir / f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        print(f"\n→ Exporting table: {table_name}")

        with app.app_context():
            try:
                # Get table data
                result = db.session.execute(text(f"SELECT * FROM {table_name}")).fetchall()

                # Get column names
                inspector = inspect(db.engine)
                columns = [col['name'] for col in inspector.get_columns(table_name)]

                # Convert to list of dicts
                data = []
                for row in result:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        # Convert datetime to string
                        if hasattr(value, 'isoformat'):
                            value = value.isoformat()
                        row_dict[col] = value
                    data.append(row_dict)

                # Write to JSON file
                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=2)

                print(f"✓ Exported {len(data)} records to: {output_file}")

            except Exception as e:
                print(f"✗ Error exporting table: {str(e)}")
                import traceback
                traceback.print_exc()


def main():
    """Main CLI entry point"""
    utils = DatabaseUtils()

    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]

    if command == 'backup':
        utils.backup()

    elif command == 'restore':
        if len(sys.argv) < 3:
            print("Error: Please specify backup file")
            print("Usage: python db_utils.py restore <backup_file>")
            return
        utils.restore(sys.argv[2])

    elif command == 'stats':
        utils.stats()

    elif command == 'check':
        utils.check()

    elif command == 'vacuum':
        utils.vacuum()

    elif command == 'export':
        if len(sys.argv) < 3:
            print("Error: Please specify table name")
            print("Usage: python db_utils.py export <table>")
            return
        utils.export_table(sys.argv[2])

    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == '__main__':
    main()
