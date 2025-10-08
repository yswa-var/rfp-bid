# 📊 CSV Storage for Session Management

## Overview

The backend now uses **CSV file persistence** for storing user sessions and user IDs. This means:

✅ **Sessions survive server restarts**  
✅ **No database required**  
✅ **Easy to inspect and debug**  
✅ **Simple file-based storage**  

## How It Works

### CSV File Structure

The `sessions.csv` file contains all active sessions with the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| `session_id` | Unique session identifier | `abc-123-def-456` |
| `user_id` | User identifier | `telegram_12345` |
| `platform` | Platform name | `telegram`, `discord`, `api` |
| `thread_id` | LangGraph conversation thread | `xyz-789-ghi-012` |
| `created_at` | Session creation timestamp | `2025-09-30T10:30:00` |
| `last_activity` | Last activity timestamp | `2025-09-30T11:45:00` |
| `pending_approval` | JSON of pending approval data | `{"tool_name": "apply_edit", ...}` |
| `metadata` | JSON of additional metadata | `{"source": "web", ...}` |

### Example CSV Content

```csv
session_id,user_id,platform,thread_id,created_at,last_activity,pending_approval,metadata
a1b2c3d4,telegram_12345,telegram,x1y2z3,2025-09-30T10:30:00,2025-09-30T11:45:00,"",{}
e5f6g7h8,discord_67890,discord,w9v8u7,2025-09-30T09:15:00,2025-09-30T11:30:00,"{""tool_name"": ""apply_edit""}",{}
i9j0k1l2,api_user123,api,t6s5r4,2025-09-30T11:00:00,2025-09-30T11:50:00,"","{""source"": ""web""}"
```

## Configuration

### Default Location

By default, `sessions.csv` is created in the `backend/` directory:

```
backend/
├── app.py
├── session_manager.py
├── sessions.csv          ← Created automatically
└── ...
```

### Custom Location

Set a custom path using environment variable:

```bash
# In .env file
SESSIONS_CSV_PATH=/path/to/my/sessions.csv
```

Or in code:

```python
from session_manager import SessionManager

# Custom path
session_manager = SessionManager(csv_file="/data/sessions.csv")
```

## Features

### 1. Automatic Save on Changes

Every time a session is created, updated, or deleted, the CSV file is automatically updated:

```python
# Creates new session and saves to CSV
session = session_manager.get_or_create_session(
    user_id="telegram_123",
    platform="telegram"
)

# Updates session and saves to CSV
session_manager.set_pending_approval(
    session_id=session.session_id,
    approval_data={"tool": "apply_edit"}
)
```

### 2. Auto-Load on Startup

When the backend starts, it automatically loads all non-expired sessions from CSV:

```
🚀 Starting backend...
📂 Loading sessions from sessions.csv...
✅ Loaded 5 sessions from sessions.csv
🌐 Server ready on http://localhost:8000
```

### 3. Expired Session Cleanup

Expired sessions (default: 60 minutes of inactivity) are:
- Not loaded on startup
- Automatically cleaned up every 5 minutes
- Removed from CSV when deleted

### 4. Thread-Safe Operations

All CSV operations are protected with locks to prevent data corruption:

```python
with self._lock:
    # Safe concurrent access
    session = self._sessions.get(session_id)
    self._save_sessions()
```

## Usage Examples

### View Sessions

You can inspect the CSV file directly:

```bash
cd backend
cat sessions.csv
```

Or use the API:

```bash
curl http://localhost:8000/api/sessions
```

### Edit Manually (Advanced)

You can manually edit the CSV file while the server is **stopped**:

```bash
# Stop the server
# Edit sessions.csv
nano sessions.csv

# Restart the server
./start.sh
```

⚠️ **Warning**: Don't edit while server is running - changes will be overwritten!

### Export/Backup

Simple backup:

```bash
cp sessions.csv sessions_backup_$(date +%Y%m%d).csv
```

### Import Sessions

Replace the CSV file:

```bash
cp old_sessions.csv sessions.csv
# Restart server
./start.sh
```

## CSV Format Details

### JSON Fields

Two fields contain JSON data:

1. **pending_approval**: 
```json
{
  "type": "approval_request",
  "tool_name": "apply_edit",
  "tool_call_id": "call_123",
  "args": {...},
  "description": "Update section..."
}
```

2. **metadata**:
```json
{
  "source": "web",
  "ip_address": "192.168.1.1",
  "custom_field": "value"
}
```

### Empty Values

- Empty `pending_approval`: No approval pending → `""`
- Empty `metadata`: No extra data → `{}`

## Monitoring

### Check Active Sessions

```bash
# Count active sessions
wc -l sessions.csv

# View sessions
column -t -s, sessions.csv | less
```

### Find Specific User

```bash
# Find all sessions for a user
grep "telegram_12345" sessions.csv
```

### Session Statistics

```bash
# Count by platform
cut -d',' -f3 sessions.csv | sort | uniq -c
```

Example output:
```
   3 api
   5 discord
   7 telegram
```

## Troubleshooting

### Problem: CSV file not created

**Solution**: Check write permissions in backend directory

```bash
cd backend
touch sessions.csv
chmod 644 sessions.csv
```

### Problem: Corrupt CSV file

**Symptoms**: Server fails to load sessions

**Solution**:
```bash
# Backup current file
mv sessions.csv sessions_corrupt.csv

# Let server create new file
./start.sh
```

### Problem: Too many old sessions

**Solution**: Manually clean up:

```bash
# Stop server
# Keep only header and recent sessions
head -1 sessions.csv > sessions_new.csv
tail -100 sessions.csv >> sessions_new.csv
mv sessions_new.csv sessions.csv
# Restart server
```

### Problem: Sessions not persisting

**Check**:
1. CSV file path is writable
2. Disk space available
3. Check server logs for errors

## Performance Considerations

### File Size

- Each session ≈ 500 bytes
- 1000 sessions ≈ 500 KB
- 10,000 sessions ≈ 5 MB

Still very manageable!

### Write Performance

The CSV is rewritten on each change. For high-traffic scenarios:

**Option 1**: Increase session timeout (fewer writes)
```python
SessionManager(session_timeout_minutes=120)  # 2 hours
```

**Option 2**: Batch writes (future enhancement)
```python
# Save only every N changes or every M seconds
```

**Option 3**: Use database (for production with 1000+ concurrent users)
```python
# Switch to Redis, PostgreSQL, or MongoDB
```

## Migration to Database

If you outgrow CSV storage, here's how to migrate:

### Export to JSON

```python
import csv
import json

sessions = []
with open('sessions.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        sessions.append(row)

with open('sessions.json', 'w') as f:
    json.dump(sessions, f, indent=2)
```

### Import to Database

```python
# PostgreSQL example
import psycopg2
import csv

conn = psycopg2.connect(database="mydb", user="user")
cur = conn.cursor()

with open('sessions.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cur.execute(
            """INSERT INTO sessions VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (row['session_id'], row['user_id'], row['platform'], 
             row['thread_id'], row['created_at'], row['last_activity'],
             row['pending_approval'], row['metadata'])
        )

conn.commit()
```

## Security

### Sensitive Data

The CSV file may contain:
- User IDs
- Platform identifiers
- Conversation threads
- Pending operations

**Recommendations**:

1. **Protect the file**:
```bash
chmod 600 sessions.csv  # Read/write for owner only
```

2. **Add to .gitignore**:
```bash
echo "backend/sessions.csv" >> .gitignore
```

3. **Encrypt backups**:
```bash
tar czf - sessions.csv | openssl enc -aes-256-cbc -out sessions_backup.tar.gz.enc
```

4. **Don't commit**:
```bash
# Already in .gitignore (recommended)
sessions.csv
sessions_*.csv
*.csv
```

## Best Practices

### Development

```bash
# Use separate CSV files per environment
SESSIONS_CSV_PATH=sessions_dev.csv
```

### Production

```bash
# Use absolute path
SESSIONS_CSV_PATH=/var/app/data/sessions.csv

# Set proper permissions
chmod 600 /var/app/data/sessions.csv
chown app:app /var/app/data/sessions.csv
```

### Testing

```python
# Use temp file for tests
import tempfile

test_csv = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
session_manager = SessionManager(csv_file=test_csv.name)
```

## Advantages of CSV Storage

✅ **Simple**: No database setup required  
✅ **Portable**: Copy file = migrate sessions  
✅ **Debuggable**: Human-readable format  
✅ **Lightweight**: Perfect for small to medium traffic  
✅ **Version control friendly**: Can diff changes  
✅ **No dependencies**: Built into Python  

## When to Upgrade

Consider migrating to a database when:

- ❌ More than 10,000 active sessions
- ❌ More than 100 writes per second
- ❌ Need distributed storage
- ❌ Need complex queries
- ❌ Need transactions

For most bot applications, **CSV is perfect**! 🎉

## Summary

The CSV-based session storage provides:

- ✅ Persistent sessions across restarts
- ✅ Easy backup and restore
- ✅ Human-readable format
- ✅ No database required
- ✅ Perfect for free deployments

---

**Questions?** Check `backend/README.md` or inspect `sessions.csv` directly!
