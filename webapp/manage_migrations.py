#!/usr/bin/env python3
"""
Database migration management script for WriteBot.

This script provides an easy interface to manage Alembic database migrations.

Usage:
    python manage_migrations.py migrate "description"  # Create new migration with autogenerate
    python manage_migrations.py upgrade                 # Run all pending migrations
    python manage_migrations.py downgrade               # Downgrade one migration
    python manage_migrations.py current                 # Show current migration
    python manage_migrations.py history                 # Show migration history
    python manage_migrations.py heads                   # Show head revisions
"""

import os
import sys
from alembic.config import Config
from alembic import command

# Get the directory containing this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to alembic.ini
ALEMBIC_INI = os.path.join(SCRIPT_DIR, 'alembic.ini')


def get_alembic_config():
    """Get Alembic configuration."""
    if not os.path.exists(ALEMBIC_INI):
        print(f"Error: alembic.ini not found at {ALEMBIC_INI}")
        sys.exit(1)
    return Config(ALEMBIC_INI)


def migrate(message=None):
    """Create a new migration with autogenerate."""
    if not message:
        print("Error: Please provide a migration message")
        print("Usage: python manage_migrations.py migrate 'your message here'")
        sys.exit(1)

    config = get_alembic_config()
    print(f"Creating new migration: {message}")
    command.revision(config, message=message, autogenerate=True)
    print("Migration created successfully!")


def upgrade(revision="head"):
    """Upgrade to a later version."""
    config = get_alembic_config()
    print(f"Upgrading database to: {revision}")
    command.upgrade(config, revision)
    print("Database upgraded successfully!")


def downgrade(revision="-1"):
    """Revert to a previous version."""
    config = get_alembic_config()
    print(f"Downgrading database to: {revision}")
    command.downgrade(config, revision)
    print("Database downgraded successfully!")


def current():
    """Show current revision."""
    config = get_alembic_config()
    print("Current database revision:")
    command.current(config)


def history():
    """Show revision history."""
    config = get_alembic_config()
    print("Migration history:")
    command.history(config)


def heads():
    """Show head revisions."""
    config = get_alembic_config()
    print("Head revisions:")
    command.heads(config)


def show_help():
    """Show help message."""
    print(__doc__)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)

    command_name = sys.argv[1].lower()

    if command_name == "migrate":
        message = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
        migrate(message)
    elif command_name == "upgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        upgrade(revision)
    elif command_name == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        downgrade(revision)
    elif command_name == "current":
        current()
    elif command_name == "history":
        history()
    elif command_name == "heads":
        heads()
    elif command_name in ["help", "-h", "--help"]:
        show_help()
    else:
        print(f"Unknown command: {command_name}")
        show_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
