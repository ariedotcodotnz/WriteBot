# WriteBot Database Migrations

This directory contains the database migration system for WriteBot. It provides a centralized, version-controlled approach to managing database schema changes.

## Overview

The migration system uses a custom Python-based migration runner that tracks applied migrations in a `migration_history` table. Each migration is numbered sequentially and can be applied or rolled back independently.

## Directory Structure

```
migrations/
├── migrate.py           # Main migration manager script
├── versions/            # Individual migration files
│   ├── 001_create_users_table.py
│   ├── 002_create_user_activities_table.py
│   ├── 003_create_usage_statistics_table.py
│   └── ...
└── README.md           # This file
```

## Quick Start

### Check Migration Status

```bash
cd webapp
python migrations/migrate.py status
```

This shows which migrations have been applied and which are pending.

### Run All Pending Migrations

```bash
python migrations/migrate.py up
```

This applies all migrations that haven't been run yet.

### Run Migrations Up To a Specific Version

```bash
python migrations/migrate.py up 005
```

This applies migrations up to and including version 005.

### Rollback to a Specific Version

```bash
python migrations/migrate.py down 003
```

This rolls back all migrations after version 003.

### Create a New Migration

```bash
python migrations/migrate.py create "add user preferences"
```

This creates a new migration file with a template you can fill in.

### Reset Database (DANGEROUS!)

```bash
python migrations/migrate.py reset
```

This drops all tables and clears migration history. You'll be prompted to confirm.

## Migration Files

### Structure

Each migration file contains two functions:

```python
def upgrade(db):
    """Apply migration changes"""
    # Your upgrade logic here
    pass

def downgrade(db):
    """Revert migration changes"""
    # Your rollback logic here
    pass
```

### Naming Convention

Migrations are named: `{version}_{description}.py`

- **version**: Three-digit number (001, 002, 003, etc.)
- **description**: Snake_case description of the change

Examples:
- `001_create_users_table.py`
- `002_add_email_verification.py`
- `010_seed_default_templates.py`

### Writing Migrations

Use SQLAlchemy's text() function for SQL queries:

```python
from sqlalchemy import text

def upgrade(db):
    db.session.execute(text("""
        CREATE TABLE example (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL
        )
    """))
    db.session.commit()
```

### Best Practices

1. **Idempotent Migrations**: Use `IF NOT EXISTS` clauses where possible
2. **Test Both Directions**: Always test both upgrade and downgrade
3. **One Logical Change**: Each migration should represent one logical change
4. **Data Migrations**: Separate schema changes from data migrations
5. **Commit Often**: Commit after each major operation within a migration

## Current Migrations

### Schema Migrations (001-008)

1. **001_create_users_table.py** - Core user authentication and profiles
2. **002_create_user_activities_table.py** - User activity tracking and audit log
3. **003_create_usage_statistics_table.py** - Daily usage metrics per user
4. **004_create_page_size_presets_table.py** - Page dimensions (A4, Letter, etc.)
5. **005_create_template_presets_table.py** - Template configurations
6. **006_create_character_override_collections_table.py** - Character override grouping
7. **007_create_character_overrides_table.py** - Custom SVG character data
8. **008_add_template_advanced_features.py** - Advanced generation features

### Data Seeding Migrations (009-010)

9. **009_seed_default_page_sizes.py** - Default page sizes (A5, A4, Letter, Legal)
10. **010_seed_default_templates.py** - Default template presets

### Optimization Migrations (011-014)

11. **011_add_performance_indexes.py** - Database performance indexes
12. **012_add_audit_triggers.py** - Automatic timestamp updates
13. **013_add_data_integrity_constraints.py** - Data validation views
14. **014_create_backup_utilities.py** - Backup and reporting views

## Database Schema

### Core Tables

- **users** - User accounts and authentication
- **user_activities** - Activity log and audit trail
- **usage_statistics** - Daily usage metrics

### Content Tables

- **page_size_presets** - Page dimension presets
- **template_presets** - Template configurations
- **character_override_collections** - Character override sets
- **character_overrides** - Individual character SVG data

### System Tables

- **migration_history** - Applied migrations tracking

### Views

- **user_summary_stats** - Aggregated user statistics
- **system_statistics** - System-wide metrics
- **recent_activity** - Recent user activity log
- **data_integrity_checks** - Data validation checks

## Troubleshooting

### Migration Failed Mid-Way

If a migration fails:

1. Check the error message
2. Fix the issue in the migration file
3. Roll back if needed: `python migrate.py down {previous_version}`
4. Re-run: `python migrate.py up`

### Database is Out of Sync

If the database schema doesn't match migration history:

1. Check status: `python migrate.py status`
2. Manually verify tables in database
3. If needed, reset and re-run: `python migrate.py reset` then `python migrate.py up`

### Can't Rollback a Migration

Some migrations (especially ALTER TABLE on SQLite) cannot be easily rolled back.
In these cases, you may need to:

1. Backup the database
2. Export data
3. Reset database
4. Re-run migrations up to desired version
5. Re-import data

## Database Backup

### Manual Backup

```bash
# Backup database file
cp webapp/instance/writebot.db webapp/instance/writebot.db.backup

# Or use SQLite dump
sqlite3 webapp/instance/writebot.db .dump > backup.sql
```

### Automated Backup

Consider setting up automated backups before running migrations in production:

```bash
# Before migrations
cp webapp/instance/writebot.db webapp/instance/writebot.db.$(date +%Y%m%d_%H%M%S)

# Run migrations
python migrations/migrate.py up
```

## Production Deployment

### Recommended Workflow

1. **Test in Development**
   ```bash
   # Test migrations locally
   python migrate.py up
   python migrate.py down {version}
   python migrate.py up
   ```

2. **Backup Production Database**
   ```bash
   cp instance/writebot.db instance/writebot.db.backup
   ```

3. **Run Migrations**
   ```bash
   python migrations/migrate.py up
   ```

4. **Verify**
   ```bash
   python migrations/migrate.py status
   # Check application functionality
   ```

5. **Rollback if Needed**
   ```bash
   python migrations/migrate.py down {previous_version}
   ```

## SQLite Limitations

Be aware of SQLite limitations:

- Cannot drop columns (requires table recreation)
- Limited ALTER TABLE support
- No native array or JSON types (use TEXT)
- Check constraints must be defined at table creation

## Advanced Usage

### Query Migration History

```bash
sqlite3 instance/writebot.db "SELECT * FROM migration_history ORDER BY version"
```

### Check Data Integrity

```bash
sqlite3 instance/writebot.db "SELECT * FROM data_integrity_checks"
```

### View System Statistics

```bash
sqlite3 instance/writebot.db "SELECT * FROM system_statistics"
```

## Contributing

When adding new migrations:

1. Create migration with descriptive name
2. Test both upgrade and downgrade
3. Document any special considerations
4. Update this README if needed
5. Commit migration file with your changes

## Support

For issues or questions:

- Check the troubleshooting section above
- Review migration file comments
- Check application logs
- Consult SQLAlchemy documentation

---

**Last Updated**: 2025-10-29
**Current Version**: 014
**Total Migrations**: 14
