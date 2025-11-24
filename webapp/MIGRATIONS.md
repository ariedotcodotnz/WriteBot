# Database Migrations with Alembic

WriteBot uses [Alembic](https://alembic.sqlalchemy.org/) for database migrations. This provides industry-standard database versioning and schema management.

## Quick Start

### Running Migrations on Deployment

When you deploy or initialize the database, migrations are run automatically:

```bash
python webapp/init_db.py
```

This will:
1. Run all pending migrations
2. Create default page sizes (A4, A5, Letter, Legal)
3. Create default templates (Standard Handwriting, Compact Notes, Large Print)
4. Optionally create admin and demo users

### Managing Migrations During Development

Use the `manage_migrations.py` helper script:

```bash
# Create a new migration (with auto-detection of model changes)
python webapp/manage_migrations.py migrate "Add new column to users table"

# Run all pending migrations
python webapp/manage_migrations.py upgrade

# Rollback one migration
python webapp/manage_migrations.py downgrade

# Show current migration version
python webapp/manage_migrations.py current

# Show migration history
python webapp/manage_migrations.py history
```

## Manual Alembic Commands

You can also use Alembic directly from the `webapp` directory:

```bash
cd webapp

# Create a new migration with auto-detection
alembic revision --autogenerate -m "description of changes"

# Create an empty migration (for data migrations)
alembic revision -m "seed default data"

# Run all pending migrations
alembic upgrade head

# Run migrations up to a specific revision
alembic upgrade abc123

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history --verbose
```

## Migration Files

Migration files are stored in `webapp/alembic/versions/`. Each migration has:

- **Revision ID**: Unique identifier
- **Down revision**: Previous migration it depends on
- **upgrade()**: Function to apply changes
- **downgrade()**: Function to revert changes

## Auto-generated vs Data Migrations

### Schema Migrations (Auto-generated)

When you change your SQLAlchemy models, Alembic can automatically detect the changes:

```bash
python webapp/manage_migrations.py migrate "Add email field to User"
```

This will create a migration that:
- Adds new columns
- Removes columns
- Changes column types
- Adds/removes indexes
- Modifies foreign keys

### Data Migrations

For seeding data or modifying existing data, create an empty migration and edit it manually:

```bash
# Using manage_migrations.py
cd webapp
alembic revision -m "Seed default settings"
```

Then edit the generated file in `alembic/versions/` to add your data operations.

Example:
```python
def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("""
        INSERT INTO settings (key, value)
        VALUES ('max_upload_size', '10MB')
    """))
```

## Best Practices

1. **Always test migrations** on a copy of your database first
2. **Review auto-generated migrations** before committing - Alembic may miss some edge cases
3. **Keep migrations small** - one logical change per migration
4. **Never edit applied migrations** - create a new migration instead
5. **Always provide downgrade()** - even for data migrations
6. **Use transactions** - migrations run in transactions and will rollback on errors

## Migrating from Old System

The old custom migration system in `webapp/migrations/` has been replaced with Alembic. The old system is deprecated and should not be used for new migrations.

If you have an existing database with the old migration system:
1. The `init_db.py` script will automatically run Alembic migrations
2. Old migrations are preserved for reference but not executed
3. All existing data is preserved

## Troubleshooting

### "Multiple head revisions present"

This means your migration chain has branched. Resolve with:
```bash
alembic merge heads -m "merge multiple heads"
```

### "Can't locate revision identified by 'xyz'"

Your migration history doesn't match the database. Check:
1. Is the database initialized?
2. Are all migration files present?
3. Run `alembic current` to see the database state

### "Target database is not up to date"

Run migrations to bring database up to date:
```bash
python webapp/manage_migrations.py upgrade
```

## Configuration

- **alembic.ini**: Main Alembic configuration file
- **alembic/env.py**: Python script that runs during migrations (configured for Flask-SQLAlchemy)
- **alembic/versions/**: Directory containing all migration files

The database URL is automatically set from your Flask app configuration.
