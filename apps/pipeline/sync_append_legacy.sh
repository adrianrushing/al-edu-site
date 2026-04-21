#!/usr/bin/env bash
set -euo pipefail

export PGCONNECT_TIMEOUT="${PGCONNECT_TIMEOUT:-8}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -f ".env" ]]; then
    echo "Missing root .env file at $REPO_ROOT/.env" >&2
    exit 1
fi

REMOTE_URL="$(python - <<'PY'
from pathlib import Path

for line in Path('.env').read_text(encoding='utf-8').splitlines():
    if line.startswith('DATABASE_URL='):
        print(line.split('=', 1)[1].strip().strip('"'))
        break
else:
    raise SystemExit('DATABASE_URL not found in .env')
PY
)"

LOCAL_URL="${LOCAL_DATABASE_URL:-postgresql://dev_user:dev_password@127.0.0.1:5433/eflt}"
SCHEMAS=(raw staging core sandbox ref)
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"

SCHEMA_ARGS=()
for schema in "${SCHEMAS[@]}"; do
    SCHEMA_ARGS+=("-n" "$schema")
done

mkdir -p backups

echo "[1/7] Preflight checks"
for required_cmd in psql pg_dump python; do
    if ! command -v "$required_cmd" >/dev/null 2>&1; then
        echo "Missing required command: $required_cmd" >&2
        exit 1
    fi
done

echo "  - Local endpoint"
psql "$LOCAL_URL" -v ON_ERROR_STOP=1 -c "SELECT 'local' AS target, inet_server_addr() AS server_addr, inet_server_port() AS server_port, current_database() AS db_name, current_user AS db_user;"

echo "  - Remote endpoint"
psql "$REMOTE_URL" -v ON_ERROR_STOP=1 -c "SELECT 'remote' AS target, inet_server_addr() AS server_addr, inet_server_port() AS server_port, current_database() AS db_name, current_user AS db_user;"

echo "[2/7] Remote safety backup"
BACKUP_PATH="backups/remote_pre_append_sync_${RUN_ID}.dump"
pg_dump -Fc --no-owner --no-privileges "${SCHEMA_ARGS[@]}" "$REMOTE_URL" > "$BACKUP_PATH"
echo "  - Backup written: $BACKUP_PATH"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
SCHEMA_SQL="$TMP_DIR/schema_sync.sql"
DATA_SQL="$TMP_DIR/data_append.sql"
SEQ_SQL="$TMP_DIR/sequence_reset.sql"
REMOTE_COUNTS="$TMP_DIR/remote_counts.csv"
LOCAL_COUNTS="$TMP_DIR/local_counts.csv"

echo "[3/7] Dump local schema"
pg_dump "$LOCAL_URL" \
    --schema-only \
    --no-owner \
    --no-privileges \
    "${SCHEMA_ARGS[@]}" \
    > "$SCHEMA_SQL"

# Local pg_dump may emit GUCs unsupported by older remote Postgres versions.
python - "$SCHEMA_SQL" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
unsupported_prefixes = (
    "SET transaction_timeout =",
)
cleaned: list[str] = []
for line in path.read_text(encoding="utf-8").splitlines():
    stripped = line.strip()
    if any(stripped.startswith(prefix) for prefix in unsupported_prefixes):
        continue
    cleaned.append(line)
path.write_text("\n".join(cleaned) + "\n", encoding="utf-8")
PY

echo "[4/7] Apply schema to remote"
psql "$REMOTE_URL" -v ON_ERROR_STOP=1 -f "$SCHEMA_SQL"

echo "[5/7] Dump local append-only data"
pg_dump "$LOCAL_URL" \
    --data-only \
    --inserts \
    --on-conflict-do-nothing \
    --no-owner \
    --no-privileges \
    "${SCHEMA_ARGS[@]}" \
    > "$DATA_SQL"

python - "$DATA_SQL" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
unsupported_prefixes = (
    "SET transaction_timeout =",
)
cleaned: list[str] = []
for line in path.read_text(encoding="utf-8").splitlines():
    stripped = line.strip()
    if any(stripped.startswith(prefix) for prefix in unsupported_prefixes):
        continue
    cleaned.append(line)
path.write_text("\n".join(cleaned) + "\n", encoding="utf-8")
PY

echo "[6/7] Apply append-only data to remote"
psql "$REMOTE_URL" -v ON_ERROR_STOP=1 -f "$DATA_SQL"

echo "[7/7] Sequence reset and materialized view refresh"
python - <<'PY' > "$SEQ_SQL"
schemas = ("raw", "staging", "core", "sandbox", "ref")
print("DO $$")
print("DECLARE")
print("    rec RECORD;")
print("    max_id BIGINT;")
print("BEGIN")
print("    FOR rec IN")
print("        SELECT")
print("            n.nspname AS schema_name,")
print("            c.relname AS table_name,")
print("            a.attname AS column_name,")
print("            pg_get_serial_sequence(format('%I.%I', n.nspname, c.relname), a.attname) AS seq_name")
print("        FROM pg_class c")
print("        JOIN pg_namespace n ON n.oid = c.relnamespace")
print("        JOIN pg_attribute a ON a.attrelid = c.oid")
print("        WHERE c.relkind = 'r'")
print("          AND n.nspname IN ('raw', 'staging', 'core', 'sandbox', 'ref')")
print("          AND a.attnum > 0")
print("          AND NOT a.attisdropped")
print("          AND pg_get_serial_sequence(format('%I.%I', n.nspname, c.relname), a.attname) IS NOT NULL")
print("    LOOP")
print("        EXECUTE format('SELECT max(%I) FROM %I.%I', rec.column_name, rec.schema_name, rec.table_name) INTO max_id;")
print("        IF max_id IS NULL THEN")
print("            EXECUTE format('SELECT setval(%L, 1, false)', rec.seq_name);")
print("        ELSE")
print("            EXECUTE format('SELECT setval(%L, %s, true)', rec.seq_name, max_id);")
print("        END IF;")
print("    END LOOP;")
print("END $$;")
print("")
print("DO $$")
print("DECLARE")
print("    mv RECORD;")
print("BEGIN")
print("    FOR mv IN")
print("        SELECT schemaname, matviewname")
print("        FROM pg_matviews")
print("        WHERE schemaname = 'core'")
print("    LOOP")
print("        BEGIN")
print("            EXECUTE format('REFRESH MATERIALIZED VIEW CONCURRENTLY %I.%I', mv.schemaname, mv.matviewname);")
print("        EXCEPTION")
print("            WHEN feature_not_supported OR object_not_in_prerequisite_state THEN")
print("                EXECUTE format('REFRESH MATERIALIZED VIEW %I.%I', mv.schemaname, mv.matviewname);")
print("        END;")
print("    END LOOP;")
print("END $$;")
PY

psql "$REMOTE_URL" -v ON_ERROR_STOP=1 -f "$SEQ_SQL"

echo "Validation: table row counts (local vs remote)"
COUNT_SQL="SELECT n.nspname || '.' || c.relname AS table_name, c.reltuples::bigint AS estimated_rows FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relkind = 'r' AND n.nspname IN ('raw','staging','core','sandbox','ref') ORDER BY 1;"
psql "$LOCAL_URL" -At -F ',' -c "$COUNT_SQL" > "$LOCAL_COUNTS"
psql "$REMOTE_URL" -At -F ',' -c "$COUNT_SQL" > "$REMOTE_COUNTS"

python - "$LOCAL_COUNTS" "$REMOTE_COUNTS" <<'PY'
import csv
import sys

local_path, remote_path = sys.argv[1], sys.argv[2]
local = {}
remote = {}

with open(local_path, newline='', encoding='utf-8') as f:
    for row in csv.reader(f):
        if not row:
            continue
        local[row[0]] = int(row[1])

with open(remote_path, newline='', encoding='utf-8') as f:
    for row in csv.reader(f):
        if not row:
            continue
        remote[row[0]] = int(row[1])

all_tables = sorted(set(local) | set(remote))
mismatches = 0
for table in all_tables:
    l = local.get(table, 0)
    r = remote.get(table, 0)
    marker = "OK" if r >= l else "BEHIND"
    if marker != "OK":
        mismatches += 1
    print(f"{marker:7} {table:50} local={l:10} remote={r:10}")

if mismatches:
    print(f"\nWARNING: {mismatches} tables are behind local.")
else:
    print("\nAll remote table estimates are >= local estimates.")
PY

echo "Append sync complete."
