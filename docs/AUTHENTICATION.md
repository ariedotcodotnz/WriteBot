# WriteBot Authentication & User Management

This document describes the secure user authentication and management system implemented in WriteBot.

## Features

### Authentication & Authorization
- ✅ **Secure Login System**: Username-based authentication with bcrypt password hashing
- ✅ **Role-Based Access Control (RBAC)**: Two roles - `user` and `admin`
- ✅ **Session Management**: Persistent sessions with "Remember Me" functionality
- ✅ **Protected Routes**: All application routes require authentication
- ✅ **No Public Signup**: User accounts can only be created by administrators

### Admin Management
- ✅ **User Management**: Create, edit, view, and delete user accounts
- ✅ **User Settings**: Manage default preferences per user
- ✅ **Activity Logging**: Track all user actions (login, logout, generations, admin actions)
- ✅ **Usage Statistics**: Monitor generation usage per user and system-wide
- ✅ **Admin Dashboard**: Overview of users, activities, and statistics

### Database
- ✅ **SQLite Database**: Lightweight, file-based database (`writebot.db`)
- ✅ **Four Main Tables**:
  - `users`: User accounts and settings
  - `user_activities`: Activity audit log
  - `usage_statistics`: Daily usage metrics per user

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The following packages are required for authentication:
- `Flask-Login`: Session management
- `Flask-SQLAlchemy`: Database ORM
- `Flask-WTF`: Form handling and CSRF protection
- `WTForms`: Form validation

### 2. Configure Environment Variables

Set a secure secret key for session encryption:

```bash
# Linux/Mac
export SECRET_KEY="your-very-secret-key-here-use-random-string"
export DATABASE_URL="sqlite:///writebot.db"  # Optional, defaults to this

# Windows
set SECRET_KEY=0ea55211309ed371c3d266185fb4123f
set DATABASE_URL=sqlite:///writebot.db
```

**Important**: Use a strong, random secret key in production!

Generate a secure key with:
```python
import secrets
print(secrets.token_hex(32))
```

### 3. Initialize Database

Run the initialization script:

```bash
python init_db.py
```

This will:
1. Create all database tables
2. Prompt you to create an admin user
3. Optionally create demo users for testing

### 4. Start the Application

```bash
python webapp/app.py
```

The application will be available at `http://localhost:5000`

## User Roles

### User (role: `user`)
- Access to the main handwriting generation interface
- Can generate SVG files and batch process
- View their own activity and statistics (future feature)
- Cannot access admin panel

### Admin (role: `admin`)
- All user permissions
- Access to admin dashboard at `/admin`
- User management (create, edit, delete, view users)
- View all activity logs
- View system-wide statistics
- Manage user settings

## Admin Panel

### Accessing the Admin Panel

1. Log in with an admin account
2. Navigate to `/admin` or click "Admin" in the navigation
3. Available sections:
   - **Dashboard**: Overview with key metrics and recent activity
   - **Users**: Manage all user accounts
   - **Activity Log**: View all user actions with filtering
   - **Statistics**: Usage metrics across different time periods

### User Management

#### Creating a User
1. Go to Admin > Users
2. Click "Create New User"
3. Fill in the form:
   - Username (required, unique)
   - Full Name (optional)
   - Password (required, min 8 characters recommended)
   - Role (user or admin)
   - Active status (checked by default)
4. Click "Create User"

#### Editing a User
1. Go to Admin > Users
2. Click "Edit" next to the user
3. Update fields (leave password blank to keep current password)
4. Click "Update User"

#### Viewing User Details
1. Go to Admin > Users
2. Click "View" next to the user
3. See:
   - User information
   - Usage statistics
   - Recent activity log

#### Deleting a User
1. Go to Admin > Users
2. Click "Delete" next to the user
3. Confirm the deletion

**Note**: You cannot delete your own account while logged in.

### Activity Tracking

All user actions are logged automatically:
- **login**: User logged in
- **logout**: User logged out
- **generate**: Single SVG generation
- **batch**: Batch generation
- **admin_action**: Admin panel actions
- **page_view**: Page access

Each log entry includes:
- User who performed the action
- Activity type
- Description
- IP address
- User agent
- Timestamp

### Usage Statistics

Statistics are tracked daily per user:
- SVG generations count
- Batch generations count
- Total lines generated
- Total characters processed
- Total processing time

Aggregate statistics available for:
- Last 7 days
- Last 30 days
- Last 90 days

## Security Features

### Password Security
- Passwords are hashed using Werkzeug's `generate_password_hash` (bcrypt)
- Passwords are never stored in plain text
- Minimum password length enforced in UI

### Session Security
- Sessions use Flask's secure session cookies
- Session cookies are HTTP-only
- Secret key used for session encryption
- Optional "Remember Me" for persistent sessions

### Route Protection
- All routes except `/auth/login` require authentication
- `@login_required` decorator on all application routes
- `@admin_required` decorator on admin routes
- Unauthorized access returns 401 or 403 errors

### Activity Auditing
- All user actions are logged
- IP addresses tracked
- User agents recorded
- Timestamps in UTC

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150),
    role VARCHAR(20) DEFAULT 'user' NOT NULL,
    is_active BOOLEAN DEFAULT 1 NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    -- User preferences
    default_style INTEGER DEFAULT 9,
    default_bias FLOAT DEFAULT 0.75,
    default_stroke_color VARCHAR(20) DEFAULT 'black',
    default_stroke_width INTEGER DEFAULT 2
);
```

### User Activities Table
```sql
CREATE TABLE user_activities (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    activity_type VARCHAR(50) NOT NULL,
    description TEXT,
    ip_address VARCHAR(45),
    user_agent VARCHAR(255),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Usage Statistics Table
```sql
CREATE TABLE usage_statistics (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    date DATE DEFAULT CURRENT_DATE,
    svg_generations INTEGER DEFAULT 0,
    batch_generations INTEGER DEFAULT 0,
    total_lines_generated INTEGER DEFAULT 0,
    total_characters_generated INTEGER DEFAULT 0,
    total_processing_time FLOAT DEFAULT 0.0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## API Changes

All API endpoints now require authentication:

- `POST /api/v1/generate` - Generate SVG (requires login)
- `POST /api/v1/generate/svg` - Generate raw SVG (requires login)
- `POST /api/generate` - Legacy endpoint (requires login)
- `POST /api/batch` - Batch generation (requires login)
- `GET /api/styles` - List styles (requires login)
- `GET /api/template-csv` - Download template (requires login)

## Development

### Creating a New Admin User Programmatically

```python
from webapp.app import app
from webapp.models import db, User

with app.app_context():
    admin = User(
        username='admin',
        full_name='Administrator',
        role='admin',
        is_active=True
    )
    admin.set_password('secure_password')
    db.session.add(admin)
    db.session.commit()
```

### Accessing User in Routes

```python
from flask_login import login_required, current_user

@app.route('/protected')
@login_required
def protected_route():
    # Access current user
    username = current_user.username
    is_admin = current_user.is_admin()
    # ... rest of your code
    return response
```

### Logging User Activity

```python
from webapp.utils.auth_utils import log_activity

# Log a simple activity
log_activity('generate', 'Generated handwriting')

# Log with metadata
log_activity('admin_action', 'Created new user',
             metadata={'new_user': 'john_doe'})
```

### Tracking Usage Statistics

```python
from webapp.utils.auth_utils import track_generation

# Track generation
track_generation(
    lines_count=10,
    chars_count=500,
    processing_time=2.5,
    is_batch=False
)
```

## Troubleshooting

### "Please log in to access this page"
- You need to log in first at `/auth/login`
- Check if your session cookie is valid

### "Your account has been disabled"
- Contact an administrator to activate your account
- Admin can enable the account in the user management panel

### "Invalid username or password"
- Double-check your credentials
- Usernames are case-sensitive
- Contact admin to reset password if needed

### Database locked errors
- SQLite database is being accessed by another process
- Close other connections or restart the application

### Secret key warning in logs
- Set the `SECRET_KEY` environment variable
- Never use the default key in production

## Production Deployment

### Security Checklist
- ✅ Set a strong, random `SECRET_KEY` environment variable
- ✅ Use HTTPS for all connections
- ✅ Enable secure cookie flags in Flask config
- ✅ Set appropriate file permissions on `writebot.db`
- ✅ Regular database backups
- ✅ Keep dependencies updated
- ✅ Monitor activity logs for suspicious behavior
- ✅ Implement rate limiting (future enhancement)
- ✅ Regular security audits

### Recommended Production Config

```python
# In production environment
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
```

## Future Enhancements

Potential improvements for the authentication system:
- Password reset functionality
- Email notifications
- Two-factor authentication (2FA)
- Rate limiting for login attempts
- User self-service password change
- OAuth integration (Google, GitHub, etc.)
- API key authentication for programmatic access
- Detailed audit reports export
- User groups and advanced permissions
- IP-based access restrictions

## Support

For issues or questions about the authentication system:
1. Check this documentation
2. Review the code in `webapp/routes/auth_routes.py` and `webapp/models.py`
3. Check activity logs in the admin panel
4. Open an issue in the project repository
