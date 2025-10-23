# Database Migrations

This directory contains database migration scripts for WriteBot.

## Running Migrations

### Add Default Presets Migration

This migration adds default page size presets (A4, A5, Letter, Legal) and template presets to the database.

**To run:**

```bash
# From the project root directory
python webapp/migrations/add_default_presets.py
```

**What it does:**
- Creates `page_size_presets` and `template_presets` tables (via SQLAlchemy's `db.create_all()`)
- Adds 4 default page size presets: A5, A4, Letter, Legal
- Adds 4 default template presets using the page sizes

**Safe to run multiple times:**
- The script checks for existing presets and skips duplicates
- Will not overwrite or delete existing data

## Migration Order

If starting with a fresh database:

1. Run `webapp/init_db.py` to create base tables and admin user
2. Run `webapp/migrations/add_default_presets.py` to add page size and template presets

## Notes

- Migrations require Flask and SQLAlchemy to be installed
- Database file location: `webapp/writebot.db` (SQLite)
- All migrations preserve existing data
