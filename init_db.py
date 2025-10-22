#!/usr/bin/env python3
"""
Database initialization script for WriteBot.

This script creates the database tables and optionally creates a default admin user.
"""
import os
import sys
from getpass import getpass

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from webapp.app import app
from webapp.models import db, User


def init_database():
    """Initialize the database tables."""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully!")


def create_admin_user():
    """Create a default admin user interactively."""
    with app.app_context():
        print("\n" + "="*50)
        print("CREATE ADMIN USER")
        print("="*50)

        # Check if admin already exists
        existing_admin = User.query.filter_by(role='admin').first()
        if existing_admin:
            print(f"\nWarning: An admin user already exists: {existing_admin.username}")
            confirm = input("Do you want to create another admin user? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Skipping admin user creation.")
                return

        # Get user details
        username = input("\nEnter admin username: ").strip()

        # Check if username exists
        if User.query.filter_by(username=username).first():
            print(f"Error: User '{username}' already exists!")
            return

        full_name = input("Enter full name (optional): ").strip()

        # Flush stdout to ensure clean transition to getpass
        sys.stdout.flush()

        # Get password with confirmation
        while True:
            password = getpass("Enter password: ")
            if len(password) < 8:
                print("Error: Password must be at least 8 characters long.")
                continue

            password_confirm = getpass("Confirm password: ")
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

        print(f"\n✓ Admin user '{username}' created successfully!")


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
            if User.query.filter_by(username=username).first():
                print(f"⊘ User '{username}' already exists, skipping...")
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

            print(f"✓ Created {user_data['role']} user: {username} (password: {user_data['password']})")


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
