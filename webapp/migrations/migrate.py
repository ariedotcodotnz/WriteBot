#!/usr/bin/env python3
"""
Database Migration Manager for WriteBot

This script manages database migrations for the WriteBot application.
It provides functionality to run, rollback, and track database migrations.

Usage:
    python migrate.py status                 # Show migration status
    python migrate.py up                     # Run all pending migrations
    python migrate.py up <version>           # Run migrations up to specific version
    python migrate.py down <version>         # Rollback to specific version
    python migrate.py create <name>          # Create a new migration file
    python migrate.py reset                  # Reset database (DANGEROUS)
"""

import os
import sys
import importlib.util
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text, inspect


class MigrationHistory(db.Model):
    """Track applied migrations"""
    __tablename__ = 'migration_history'

    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Migration {self.version}: {self.name}>'


class MigrationManager:
    """Manages database migrations"""

    def __init__(self):
        self.migrations_dir = Path(__file__).parent / 'versions'
        self.migrations_dir.mkdir(exist_ok=True)

    def ensure_migration_table(self):
        """Create migration_history table if it doesn't exist"""
        with app.app_context():
            inspector = inspect(db.engine)
            if 'migration_history' not in inspector.get_table_names():
                # Create only the migration_history table
                MigrationHistory.__table__.create(db.engine, checkfirst=True)
                print("[OK] Created migration_history table")

    def get_migration_files(self):
        """Get all migration files sorted by version"""
        migrations = []
        for file in self.migrations_dir.glob('*.py'):
            if file.name.startswith('_'):
                continue
            # Expected format: 001_create_users_table.py
            parts = file.stem.split('_', 1)
            if len(parts) == 2:
                version, name = parts
                migrations.append({
                    'version': version,
                    'name': name,
                    'file': file,
                    'full_name': file.stem
                })
        return sorted(migrations, key=lambda x: x['version'])

    def get_applied_migrations(self):
        """Get list of applied migrations from database"""
        with app.app_context():
            self.ensure_migration_table()
            return [m.version for m in MigrationHistory.query.order_by(MigrationHistory.version).all()]

    def load_migration_module(self, filepath):
        """Dynamically load a migration module"""
        spec = importlib.util.spec_from_file_location("migration", filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def run_migration(self, migration):
        """Run a single migration"""
        print(f"\n>> Running migration {migration['version']}: {migration['name']}")

        try:
            module = self.load_migration_module(migration['file'])

            with app.app_context():
                # Run the upgrade function
                if hasattr(module, 'upgrade'):
                    module.upgrade(db)

                    # Record in migration history
                    history = MigrationHistory(
                        version=migration['version'],
                        name=migration['name']
                    )
                    db.session.add(history)
                    db.session.commit()

                    print(f"[OK] Successfully applied migration {migration['version']}")
                else:
                    print(f"[ERROR] Migration {migration['version']} has no upgrade() function")
                    return False

            return True

        except Exception as e:
            print(f"[ERROR] Error running migration {migration['version']}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def rollback_migration(self, migration):
        """Rollback a single migration"""
        print(f"\n>> Rolling back migration {migration['version']}: {migration['name']}")

        try:
            module = self.load_migration_module(migration['file'])

            with app.app_context():
                # Run the downgrade function
                if hasattr(module, 'downgrade'):
                    module.downgrade(db)

                    # Remove from migration history
                    MigrationHistory.query.filter_by(version=migration['version']).delete()
                    db.session.commit()

                    print(f"[OK] Successfully rolled back migration {migration['version']}")
                else:
                    print(f"[ERROR] Migration {migration['version']} has no downgrade() function")
                    return False

            return True

        except Exception as e:
            print(f"[ERROR] Error rolling back migration {migration['version']}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def status(self):
        """Show migration status"""
        print("\n" + "="*60)
        print("DATABASE MIGRATION STATUS")
        print("="*60)

        migrations = self.get_migration_files()
        applied = self.get_applied_migrations()

        if not migrations:
            print("\nNo migration files found.")
            return

        print(f"\nTotal migrations: {len(migrations)}")
        print(f"Applied: {len(applied)}")
        print(f"Pending: {len(migrations) - len(applied)}")
        print("\n" + "-"*60)
        print(f"{'VERSION':<10} {'STATUS':<10} {'NAME'}")
        print("-"*60)

        for migration in migrations:
            status = "[X] Applied" if migration['version'] in applied else "[ ] Pending"
            print(f"{migration['version']:<10} {status:<15} {migration['name']}")

        print("="*60 + "\n")

    def migrate_up(self, target_version=None):
        """Run pending migrations up to target version"""
        migrations = self.get_migration_files()
        applied = self.get_applied_migrations()

        pending = [m for m in migrations if m['version'] not in applied]

        if target_version:
            pending = [m for m in pending if m['version'] <= target_version]

        if not pending:
            print("\n[OK] No pending migrations to apply.")
            return

        print(f"\n>> Found {len(pending)} pending migration(s)")

        for migration in pending:
            if not self.run_migration(migration):
                print("\n[ERROR] Migration failed. Stopping.")
                return

        print("\n[OK] All migrations applied successfully!")

    def migrate_down(self, target_version):
        """Rollback migrations down to target version"""
        migrations = self.get_migration_files()
        applied = self.get_applied_migrations()

        # Get migrations to rollback (in reverse order)
        to_rollback = [m for m in reversed(migrations) if m['version'] in applied and m['version'] > target_version]

        if not to_rollback:
            print(f"\n[OK] Already at version {target_version} or lower.")
            return

        print(f"\n>> Found {len(to_rollback)} migration(s) to rollback")

        for migration in to_rollback:
            if not self.rollback_migration(migration):
                print("\n[ERROR] Rollback failed. Stopping.")
                return

        print(f"\n[OK] Successfully rolled back to version {target_version}!")

    def create_migration(self, name):
        """Create a new migration file"""
        migrations = self.get_migration_files()

        # Get next version number
        if migrations:
            last_version = int(migrations[-1]['version'])
            next_version = f"{last_version + 1:03d}"
        else:
            next_version = "001"

        # Create filename
        safe_name = name.lower().replace(' ', '_').replace('-', '_')
        filename = f"{next_version}_{safe_name}.py"
        filepath = self.migrations_dir / filename

        # Create migration template
        template = f'''"""
Migration {next_version}: {name}

Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

from sqlalchemy import text


def upgrade(db):
    """Apply migration changes"""
    # TODO: Implement upgrade logic
    # Example:
    # db.session.execute(text("""
    #     CREATE TABLE example (
    #         id INTEGER PRIMARY KEY,
    #         name VARCHAR(100) NOT NULL
    #     )
    # """))
    # db.session.commit()
    pass


def downgrade(db):
    """Revert migration changes"""
    # TODO: Implement downgrade logic
    # Example:
    # db.session.execute(text("DROP TABLE example"))
    # db.session.commit()
    pass
'''

        filepath.write_text(template)
        print(f"\n[OK] Created migration file: {filename}")
        print(f"  Path: {filepath}")
        print(f"\nEdit the file to add your migration logic.")

    def reset_database(self):
        """Reset database - DROP ALL TABLES (DANGEROUS)"""
        print("\n" + "!"*60)
        print("WARNING: This will DELETE ALL DATA in the database!")
        print("!"*60)

        confirm = input("\nType 'YES' to confirm: ")
        if confirm != 'YES':
            print("Aborted.")
            return

        with app.app_context():
            print("\n>> Dropping all tables...")
            db.drop_all()
            print("[OK] All tables dropped")

            print(">> Clearing migration history...")
            # Migration history is already dropped, just recreate it
            self.ensure_migration_table()
            print("[OK] Database reset complete")


def main():
    """Main CLI entry point"""
    manager = MigrationManager()

    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]

    if command == 'status':
        manager.status()

    elif command == 'up':
        target = sys.argv[2] if len(sys.argv) > 2 else None
        manager.migrate_up(target)

    elif command == 'down':
        if len(sys.argv) < 3:
            print("Error: Please specify target version")
            print("Usage: python migrate.py down <version>")
            return
        manager.migrate_down(sys.argv[2])

    elif command == 'create':
        if len(sys.argv) < 3:
            print("Error: Please specify migration name")
            print("Usage: python migrate.py create <name>")
            return
        manager.create_migration(' '.join(sys.argv[2:]))

    elif command == 'reset':
        manager.reset_database()

    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == '__main__':
    main()
