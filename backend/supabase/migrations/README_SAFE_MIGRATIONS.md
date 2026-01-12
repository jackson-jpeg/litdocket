# SAFE MIGRATION RULES

## ⚠️ NEVER DO THESE:

### ❌ DON'T DROP TABLES WITH DATA
```sql
-- NEVER DO THIS if table has data:
DROP TABLE IF EXISTS deadlines CASCADE;
```

### ❌ DON'T ALTER WITHOUT BACKUP
```sql
-- NEVER alter columns without checking data first
ALTER TABLE deadlines ALTER COLUMN user_id TYPE UUID;
```

## ✅ SAFE PATTERNS:

### ✅ Adding Columns (Always Safe)
```sql
-- Safe: adds column without touching existing data
ALTER TABLE deadlines
ADD COLUMN IF NOT EXISTS new_field VARCHAR(255);
```

### ✅ Adding Indexes (Always Safe)
```sql
-- Safe: only adds index, doesn't touch data
CREATE INDEX IF NOT EXISTS idx_deadlines_status
ON deadlines(status);
```

### ✅ Creating New Tables (Always Safe)
```sql
-- Safe: creates new table, doesn't affect existing tables
CREATE TABLE IF NOT EXISTS new_table (
    id VARCHAR(36) PRIMARY KEY,
    ...
);
```

### ✅ Converting Column Types (PRESERVE DATA)
```sql
-- Safe: converts UUID to VARCHAR while preserving data
ALTER TABLE existing_table
ALTER COLUMN id TYPE VARCHAR(36) USING id::text;
```

## 🔄 BEFORE RUNNING ANY MIGRATION:

1. **Check if table has data:**
   ```sql
   SELECT COUNT(*) FROM table_name;
   ```

2. **If table has data, NEVER drop it**

3. **Test migration on a copy first** (if making destructive changes)

## 📝 MIGRATION CHECKLIST:

- [ ] Does this migration DROP any tables? → If YES and table has data, STOP
- [ ] Does this migration ALTER column types? → If YES, verify USING clause preserves data
- [ ] Does this migration add constraints? → If YES, verify existing data satisfies them
- [ ] Have I tested this on a backup database first?

## 🚨 RED FLAGS:

If you see these keywords, STOP and review carefully:
- `DROP TABLE`
- `TRUNCATE`
- `DELETE FROM`
- `ALTER COLUMN ... TYPE` (without USING clause)
