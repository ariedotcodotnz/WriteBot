# Database Migrations

WriteBot now includes a comprehensive database migration system located in `webapp/migrations/`.

## Quick Start

```bash
cd webapp

# Check migration status
python migrations/migrate.py status

# Run all pending migrations
python migrations/migrate.py up

# Backup database before changes
python migrations/db_utils.py backup
```

## Features

- **Version Control**: All database changes are tracked in numbered migration files
- **Rollback Support**: Ability to rollback to previous database versions
- **Automatic Tracking**: Migration history is stored in `migration_history` table
- **Backup Tools**: Built-in database backup and restore utilities
- **Data Seeding**: Default data (page sizes, templates) automatically seeded
- **Performance**: Includes optimized indexes and triggers
- **Reporting**: Built-in views for statistics and data integrity checks

## What's Included

### 14 Migration Scripts

1. **Schema Migrations** (001-008)
   - Users, activities, and statistics tables
   - Page size and template presets
   - Character override system
   - Advanced template features

2. **Data Seeding** (009-010)
   - Default page sizes (A5, A4, Letter, Legal)
   - Default templates (Standard, Compact, Large Print)

3. **Optimizations** (011-014)
   - Performance indexes on key columns
   - Automatic timestamp update triggers
   - Data integrity validation views
   - Backup and reporting utilities

### Management Tools

- **migrate.py** - Main migration runner
  - Run/rollback migrations
  - Check status
  - Create new migrations
  - Reset database

- **db_utils.py** - Database utilities
  - Backup/restore database
  - View statistics
  - Check data integrity
  - Optimize database (VACUUM)
  - Export tables to JSON

### Documentation

- **README.md** - Comprehensive documentation
- **QUICKSTART.md** - 5-minute quick start guide
- **This file** - Overview and summary

## Migration System Architecture

```
webapp/migrations/
├── migrate.py              # Migration manager
├── db_utils.py             # Database utilities
├── __init__.py             # Package initialization
├── .gitignore              # Ignore backups and cache
├── README.md               # Full documentation
├── QUICKSTART.md           # Quick start guide
├── versions/               # Migration files
│   ├── 001_create_users_table.py
│   ├── 002_create_user_activities_table.py
│   └── ... (14 total migrations)
└── backups/                # Database backups (ignored by git)
```

## Database Schema

After running all migrations, you'll have:

### Tables
- users
- user_activities
- usage_statistics
- page_size_presets
- template_presets
- character_override_collections
- character_overrides
- migration_history

### Views
- user_summary_stats
- system_statistics
- recent_activity
- data_integrity_checks

### Indexes
- 20+ optimized indexes for fast queries

### Triggers
- Automatic timestamp updates

## Usage Examples

### For Development

```bash
# Create a new migration
python migrations/migrate.py create "add email to users"

# Edit the file: webapp/migrations/versions/015_add_email_to_users.py

# Test it
python migrations/migrate.py up

# Rollback if needed
python migrations/migrate.py down 014

# Re-test
python migrations/migrate.py up
```

### For Production

```bash
# Before deployment
python migrations/db_utils.py backup

# Deploy code with new migrations

# Run migrations
python migrations/migrate.py up

# Verify
python migrations/migrate.py status
python migrations/db_utils.py check
```

### Database Maintenance

```bash
# View statistics
python migrations/db_utils.py stats

# Check data integrity
python migrations/db_utils.py check

# Optimize database
python migrations/db_utils.py vacuum

# Export table
python migrations/db_utils.py export users
```

## Benefits

1. **Version Control** - All schema changes are tracked in git
2. **Reproducibility** - Fresh database can be created from migrations
3. **Team Collaboration** - Multiple developers can work on schema changes
4. **Deployment Safety** - Rollback capability for production
5. **Documentation** - Migration files serve as schema change history
6. **Automation** - Can be integrated into CI/CD pipelines

## Integration with Existing Code

The migration system is designed to work alongside the existing database initialization:

- **Old way**: `python init_db.py` (still works)
- **New way**: `python migrations/migrate.py up` (recommended)

Existing databases can be migrated by:

1. Running migrations on a fresh database
2. Comparing schemas
3. Exporting data from old database
4. Importing into new database

Or simply mark all migrations as applied if schema matches:

```python
from app import app, db
from migrations.migrate import MigrationHistory

with app.app_context():
    for version in ['001', '002', ...]:
        history = MigrationHistory(version=version, name='...')
        db.session.add(history)
    db.session.commit()
```

## Next Steps

1. Read the [Quick Start Guide](webapp/migrations/QUICKSTART.md)
2. Read the [Full Documentation](webapp/migrations/README.md)
3. Run `python migrations/migrate.py status` to see current state
4. Consider running migrations in your deployment process

## Maintenance

The migration system is self-contained and requires no external dependencies beyond what WriteBot already uses (Flask-SQLAlchemy, SQLite).

For questions or issues, refer to the troubleshooting section in `webapp/migrations/README.md`.

---

**Version**: 1.0.0
**Total Migrations**: 14
**Created**: 2025-10-29
