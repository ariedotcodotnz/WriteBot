#!/usr/bin/env python3
"""
Quick script to create demo users for WriteBot using direct SQL.
"""
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

def create_demo_users():
    """
    Create demo users for testing.

    Connects to the SQLite database and creates admin and regular user accounts
    if they don't already exist.
    """
    print("=" * 50)
    print("CREATE DEMO USERS")
    print("=" * 50)

    # Connect to database
    db_path = 'writebot.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check existing users
    cursor.execute("SELECT username, role FROM users")
    existing = cursor.fetchall()
    print(f'\nExisting users in database: {len(existing)}')
    if existing:
        for username, role in existing:
            print(f'  - {username} (role: {role})')

    # Demo users to create
    demo_users = [
        {
            'username': 'test_admin',
            'full_name': 'Test Admin',
            'role': 'admin',
            'password': 'admin123456'
        },
        {
            'username': 'demo_user',
            'full_name': 'Demo User',
            'role': 'user',
            'password': 'demo123456'
        }
    ]

    print(f'\nCreating demo users...')
    for user_data in demo_users:
        username = user_data['username']

        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            print(f'  [SKIP] User "{username}" already exists')
            continue

        # Create password hash
        password_hash = generate_password_hash(user_data['password'])
        created_at = datetime.utcnow().isoformat()

        # Insert user
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, role, is_active, created_at,
                             default_style, default_bias, default_stroke_color, default_stroke_width)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            username,
            password_hash,
            user_data['full_name'],
            user_data['role'],
            1,  # is_active
            created_at,
            9,  # default_style
            0.75,  # default_bias
            'black',  # default_stroke_color
            2  # default_stroke_width
        ))

        conn.commit()
        print(f'  [OK] Created {user_data["role"]:5s} user: {username:15s} (password: {user_data["password"]})')

    # Close connection
    conn.close()

    print('\n' + '=' * 50)
    print('DEMO USERS SUMMARY')
    print('=' * 50)
    print('\nAdmin User:')
    print('  Username: test_admin')
    print('  Password: admin123456')
    print('\nRegular User:')
    print('  Username: demo_user')
    print('  Password: demo123456')
    print('\n' + '=' * 50)

if __name__ == '__main__':
    create_demo_users()
