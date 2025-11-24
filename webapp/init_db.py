#!/usr/bin/env python3
"""
Database initialization script for WriteBot.

This script creates the database tables and optionally creates a default admin user.
"""
import os
import sys
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
    """Safely get password input with fallback for non-TTY environments."""
    # Check if we have a TTY
    if not sys.stdin.isatty():
        warnings.warn("No TTY detected - password input will be visible!")
        return input(prompt).strip()

    try:
        return getpass(prompt).strip()
    except Exception as e:
        print(f"\nWarning: getpass failed ({e}), falling back to visible input")
        return input(prompt).strip()


def init_database():
    """Initialize the database tables and run migrations."""
    with app.app_context():
        print("Running database migrations...")
        from alembic.config import Config
        from alembic import command

        # Get the alembic config
        alembic_cfg = Config(os.path.join(PROJECT_ROOT, "alembic.ini"))

        try:
            # Run all pending migrations
            command.upgrade(alembic_cfg, "head")
            print("Database migrations completed successfully!")
        except Exception as e:
            print(f"Error running migrations: {e}")
            print("\nFalling back to db.create_all()...")
            db.create_all()
            print("Database tables created successfully!")


def create_admin_user():
    """Create a default admin user interactively."""
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
    """Create demo users for testing."""
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
    """Main initialization routine."""
    print("WriteBot Database Initialization")
    print("="*50)

    # Initialize database
    init_database()

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
