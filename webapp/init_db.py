#!/usr/bin/env python3
"""
Database initialization script for WriteBot.

This script creates the database tables and optionally creates a default admin user.
"""
import os
import sys
from datetime import datetime
from getpass import getpass
import warnings

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import app first to ensure proper initialization
from app import app, db
from models import User


def get_password_input(prompt="Password: "):
    """
    Safely get password input with fallback for non-TTY environments.

    Args:
        prompt: Prompt to display to the user.

    Returns:
        The entered password as a string.
    """
    # Check if we have a TTY
    if not sys.stdin.isatty():
        warnings.warn("No TTY detected - password input will be visible!")
        return input(prompt).strip()

    try:
        return getpass(prompt).strip()
    except Exception as e:
        print(f"\nWarning: getpass failed ({e}), falling back to visible input")
        return input(prompt).strip()


def _placeholder_for(column):
    """Return a safe non-null backfill value for a newly-added NOT NULL column."""
    from sqlalchemy import Integer, Numeric, Float, Boolean, DateTime, Date
    col_type = column.type
    if isinstance(col_type, (Integer, Numeric, Float)):
        return 0
    if isinstance(col_type, Boolean):
        return False
    if isinstance(col_type, (DateTime, Date)):
        return datetime.utcnow()
    return ''  # strings/text and anything else


def _reconcile_missing_columns():
    """Add columns present in the models but missing from existing tables.

    ``db.create_all()`` creates new tables but never ALTERs existing ones, so a DB
    created against older models is left missing newly-added columns -- which is
    exactly how ``users.email`` went missing and made every page 500. For each
    existing table we add any missing column (NOT NULL columns are backfilled so
    the ALTER succeeds on populated tables; unique columns get a unique index when
    the current values allow it). Column drops / renames / type changes are NOT
    handled here -- those need a real Alembic migration.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())
    added = []

    for table in db.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue  # brand-new table: db.create_all() already created it
        db_cols = {c['name'] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in db_cols:
                continue
            col_type = column.type.compile(dialect=db.engine.dialect)
            with db.engine.begin() as conn:
                conn.execute(text(
                    f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}'))
                if not column.nullable:
                    conn.execute(
                        text(f'UPDATE "{table.name}" SET "{column.name}" = :val '
                             f'WHERE "{column.name}" IS NULL'),
                        {"val": _placeholder_for(column)})
                if column.unique:
                    dupes = conn.execute(text(
                        f'SELECT COUNT(*) - COUNT(DISTINCT "{column.name}") '
                        f'FROM "{table.name}"')).scalar()
                    if not dupes:
                        conn.execute(text(
                            f'CREATE UNIQUE INDEX IF NOT EXISTS '
                            f'"ix_{table.name}_{column.name}" '
                            f'ON "{table.name}" ("{column.name}")'))
                    else:
                        print(f"  [WARN] added {table.name}.{column.name} but left it "
                              f"non-unique: existing rows have blank/duplicate values; "
                              f"set them and add a unique index manually.")
            added.append(f"{table.name}.{column.name}")

    if added:
        print(f"  Added missing columns: {', '.join(added)}")
    else:
        print("  Schema already matches models (no missing columns).")
    return added


def init_database():
    """
    Bring the database schema up to date from any starting state.

    Handles all three cases the app can encounter:
      * Fresh DB, or a legacy DB created by db.create_all() with no Alembic stamp:
        build the schema directly from the models (creating missing tables AND
        adding columns missing from existing tables), then stamp Alembic head so
        future `flask db upgrade` works.
      * Alembic-managed DB: apply any pending migrations with `upgrade head`.

    The previous version ran migrations first and fell back to db.create_all() on
    error, which could not ALTER existing tables and silently left the schema out
    of date (the users.email outage).
    """
    with app.app_context():
        # Use Flask-Migrate's helpers (not a hand-built alembic Config): they use
        # the Migrate extension's configured migrations/ directory. The old code
        # pointed Config at webapp/alembic.ini -> webapp/alembic/env.py, which does
        # not exist, so every `upgrade` failed and silently fell back to
        # create_all() -- the reason the schema drifted (users.email outage).
        from flask_migrate import upgrade as fm_upgrade, stamp as fm_stamp
        from alembic.runtime.migration import MigrationContext

        with db.engine.connect() as conn:
            current_rev = MigrationContext.configure(conn).get_current_revision()

        if current_rev is None:
            print("No Alembic revision found - syncing schema directly from models...")
            db.create_all()                # create any missing tables
            _reconcile_missing_columns()   # add columns missing from existing tables
            fm_stamp(revision="head")      # mark as current so future upgrades work
            print("Schema synced from models and stamped to Alembic head.")
        else:
            print(f"Alembic revision {current_rev} - applying any pending migrations...")
            try:
                fm_upgrade()               # to head
                print("Database is at Alembic head.")
            except Exception as e:
                print(f"Error applying migrations: {e}")
                print("Falling back to model-based schema sync...")
                db.create_all()
                _reconcile_missing_columns()


def create_admin_user():
    """
    Create a default admin user interactively.

    Prompts for username, full name, and password (with confirmation).
    Ensures the username is unique.
    """
    with app.app_context():
        print("\n" + "="*50)
        print("CREATE ADMIN USER")
        print("="*50)

        # Check if admin already exists
        existing_admin = db.session.query(User).filter_by(role='admin').first()
        if existing_admin:
            print(f"\nWarning: An admin user already exists: {existing_admin.username}")
            confirm = input("Do you want to create another admin user? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Skipping admin user creation.")
                return

        # Get user details
        username = input("\nEnter admin username: ").strip()

        # Check if username exists
        if db.session.query(User).filter_by(username=username).first():
            print(f"Error: User '{username}' already exists!")
            return

        full_name = input("Enter full name (optional): ").strip()

        # Get password with confirmation
        print()  # Add blank line for better readability
        while True:
            password = get_password_input("Enter password: ")
            if len(password) < 8:
                print("Error: Password must be at least 8 characters long.")
                continue

            password_confirm = get_password_input("Confirm password: ")
            if password != password_confirm:
                print("Error: Passwords do not match!")
                continue

            break

        # Create admin user
        admin = User(
            username=username,
            full_name=full_name or None,
            role='admin',
            is_active=True
        )
        admin.set_password(password)

        db.session.add(admin)
        db.session.commit()

        print(f"\n[OK] Admin user '{username}' created successfully!")


def create_demo_users():
    """
    Create demo users for testing.

    Interactively asks to create a standard demo user and an admin user
    if they don't exist.
    """
    with app.app_context():
        print("\n" + "="*50)
        print("CREATE DEMO USERS")
        print("="*50)

        confirm = input("\nDo you want to create demo users? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Skipping demo user creation.")
            return

        demo_users = [
            {
                'username': 'demo_user',
                'full_name': 'Demo User',
                'role': 'user',
                'password': 'demo123456'
            },
            {
                'username': 'test_admin',
                'full_name': 'Test Admin',
                'role': 'admin',
                'password': 'admin123456'
            }
        ]

        for user_data in demo_users:
            username = user_data['username']

            # Check if user already exists
            if db.session.query(User).filter_by(username=username).first():
                print(f"[SKIP] User '{username}' already exists, skipping...")
                continue

            user = User(
                username=username,
                full_name=user_data['full_name'],
                role=user_data['role'],
                is_active=True
            )
            user.set_password(user_data['password'])

            db.session.add(user)
            db.session.commit()

            print(f"[OK] Created {user_data['role']} user: {username} (password: {user_data['password']})")


def main():
    """
    Main initialization routine.

    Parses command line arguments and orchestrates the initialization process.
    """
    import argparse

    parser = argparse.ArgumentParser(description='Initialize WriteBot database')
    parser.add_argument('--auto', action='store_true',
                        help='Run in automatic mode (non-interactive, for production)')
    args = parser.parse_args()

    if not args.auto:
        print("WriteBot Database Initialization")
        print("="*50)

    # Initialize database
    init_database()

    if args.auto:
        # Automatic mode - just run migrations and exit
        print("Database initialization completed (auto mode)")
        return

    # Interactive mode - create admin user and demo users
    # Create admin user
    create_admin = input("\nDo you want to create an admin user? (y/n): ").strip().lower()
    if create_admin == 'y':
        create_admin_user()

    # Ask about demo users
    create_demo_users()

    print("\n" + "="*50)
    print("Database initialization complete!")
    print("="*50)
    print("\nYou can now run the application with:")
    print("  python webapp/app.py")


if __name__ == '__main__':
    main()