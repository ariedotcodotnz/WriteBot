# Database Migration Quick Start Guide

Get started with WriteBot database migrations in 5 minutes!

## Installation

No installation needed! The migration system uses Python and SQLAlchemy, which are already part of WriteBot's dependencies.

## Your First Migration

### 1. Check Current Status

```bash
cd webapp
python migrations/migrate.py status
```

You should see something like:

```
DATABASE MIGRATION STATUS
============================================================
Total migrations: 14
Applied: 0
Pending: 14

VERSION    STATUS     NAME
------------------------------------------------------------
001        ○ Pending  create_users_table
002        ○ Pending  create_user_activities_table
...
```

### 2. Run All Migrations

```bash
python migrations/migrate.py up
```

This will:
- Create all tables
- Add indexes for performance
- Seed default data (page sizes, templates)
- Set up audit triggers and views

### 3. Verify Success

```bash
python migrations/migrate.py status
```

Now all migrations should show "✓ Applied":

```
VERSION    STATUS     NAME
------------------------------------------------------------
001        ✓ Applied  create_users_table
002        ✓ Applied  create_user_activities_table
...
```

### 4. Check Database Stats

```bash
python migrations/db_utils.py stats
```

This shows:
- Number of tables and records
- Database file size
- System statistics

## Common Tasks

### Create a New Migration

```bash
python migrations/migrate.py create "add user email field"
```

This creates: `webapp/migrations/versions/015_add_user_email_field.py`

Edit the file:

```python
def upgrade(db):
    """Apply migration changes"""
    db.session.execute(text("""
        ALTER TABLE users
        ADD COLUMN email VARCHAR(120)
    """))
    db.session.commit()

def downgrade(db):
    """Revert migration changes"""
    # SQLite doesn't support DROP COLUMN easily
    print("⚠ Manual rollback required")
```

Then run it:

```bash
python migrations/migrate.py up
```

### Backup Database Before Migrations

```bash
python migrations/db_utils.py backup
```

Creates: `webapp/migrations/backups/writebot_20251029_143022.db`

### Restore from Backup

```bash
python migrations/db_utils.py restore backups/writebot_20251029_143022.db
```

### Rollback Last Migration

First, check what's applied:

```bash
python migrations/migrate.py status
```

Then rollback to previous version:

```bash
python migrations/migrate.py down 013
```

This rolls back everything after version 013.

### Export Table Data

```bash
python migrations/db_utils.py export users
```

Creates: `webapp/migrations/backups/users_20251029_143022.json`

### Check Data Integrity

```bash
python migrations/db_utils.py check
```

Shows:
- Invalid data in tables
- Orphaned foreign key references
- Data consistency issues

### Optimize Database

```bash
python migrations/db_utils.py vacuum
```

Reclaims unused space and optimizes the SQLite database.

## Migration Workflow

### Development

1. **Create migration**
   ```bash
   python migrations/migrate.py create "my change"
   ```

2. **Edit migration file**
   - Add upgrade logic
   - Add downgrade logic

3. **Test upgrade**
   ```bash
   python migrations/migrate.py up
   ```

4. **Test downgrade**
   ```bash
   python migrations/migrate.py down {previous_version}
   ```

5. **Test upgrade again**
   ```bash
   python migrations/migrate.py up
   ```

6. **Commit to git**
   ```bash
   git add webapp/migrations/versions/*.py
   git commit -m "Add database migration for my change"
   ```

### Production

1. **Backup database**
   ```bash
   python migrations/db_utils.py backup
   ```

2. **Check migration status**
   ```bash
   python migrations/migrate.py status
   ```

3. **Run migrations**
   ```bash
   python migrations/migrate.py up
   ```

4. **Verify**
   ```bash
   python migrations/migrate.py status
   python migrations/db_utils.py check
   ```

5. **If issues, rollback**
   ```bash
   python migrations/migrate.py down {previous_version}
   ```

## Troubleshooting

### "Table already exists"

The migration is trying to create a table that exists. Either:

1. The migration was already applied manually
2. The migration_history is out of sync

**Solution**: Mark migration as applied manually:

```python
from app import app, db
from migrations.migrate import MigrationHistory

with app.app_context():
    history = MigrationHistory(version='001', name='create_users_table')
    db.session.add(history)
    db.session.commit()
```

### "No such table: migration_history"

The migration system hasn't been initialized.

**Solution**: Just run `status` or `up` - the table will be created automatically:

```bash
python migrations/migrate.py status
```

### Migration Failed Halfway

**Solution**:

1. Check the error message
2. Fix the issue in the migration file
3. Remove the failed entry from migration_history:

```python
from app import app, db
from migrations.migrate import MigrationHistory

with app.app_context():
    MigrationHistory.query.filter_by(version='015').delete()
    db.session.commit()
```

4. Re-run the migration

### Need to Reset Everything

**DANGER**: This deletes all data!

```bash
python migrations/migrate.py reset
python migrations/migrate.py up
```

## File Locations

- **Migration scripts**: `webapp/migrations/versions/`
- **Database file**: `webapp/instance/writebot.db`
- **Backups**: `webapp/migrations/backups/`
- **Documentation**: `webapp/migrations/README.md`

## Next Steps

- Read the full documentation: [README.md](README.md)
- Check existing migrations in `versions/` for examples
- Set up automated backups in your deployment process
- Consider using migration versioning in your release process

## Help

Need help?

```bash
python migrations/migrate.py           # Show help
python migrations/db_utils.py          # Show utilities help
```

---

Happy migrating! 🚀
