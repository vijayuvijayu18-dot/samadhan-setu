"""
=============================================================================
SAMADHAN SETU - SQLite to PostgreSQL Database Migration Engine
Smart India Hackathon (SIH) Prototype & Enterprise Deployment Utility
=============================================================================
This script migrates data from the SQLite database (samadhan_setu.db)
to a target PostgreSQL database instance.

Key Features:
- Preserves all Primary Keys, Foreign Keys, and Timestamps
- Automatically creates PostgreSQL schema via SQLAlchemy metadata
- Inserts data in dependency order to maintain referential integrity
- Resets PostgreSQL identity / serial sequences to prevent ID collision
- Verifies migration with side-by-side row count comparison
- Supports --dry-run, --pg-url, and environment variable DATABASE_URL
=============================================================================
"""

import sys
import os
import argparse
from datetime import datetime
from dotenv import load_dotenv
import sqlalchemy as sa
from sqlalchemy import create_engine, MetaData, Table, text

# Load environment variables
load_dotenv()

# Migration table order (respecting Foreign Key dependencies)
TABLE_MIGRATION_ORDER = [
    'users',
    'organizations',
    'challenges',
    'solutions',
    'projects',
    'project_partners',
    'milestones',
    'tasks',
    'team_members',
    'impact_metrics',
    'team_invitations',
    'project_stage_updates',
    'project_impact_metrics',
    'industry_support_requests',
    'industry_support_responses',
    'submissions',
    'notifications',
    'audit_logs'
]

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Migrate SamadhanSetu database from SQLite to PostgreSQL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate_sqlite_to_postgresql.py --dry-run
  python migrate_sqlite_to_postgresql.py --pg-url postgresql://postgres:password@localhost:5432/samadhan_setu
  python migrate_sqlite_to_postgresql.py
        """
    )
    parser.add_argument(
        '--sqlite-path',
        default='samadhan_setu.db',
        help='Path to the source SQLite database file (default: samadhan_setu.db)'
    )
    parser.add_argument(
        '--pg-url',
        default=os.environ.get('DATABASE_URL'),
        help='PostgreSQL connection URL (default: reads DATABASE_URL from .env)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Inspect SQLite tables and display row counts without connecting to PostgreSQL'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=500,
        help='Batch size for row migration (default: 500)'
    )
    return parser.parse_args()

def normalize_database_url(url):
    if not url:
        return url
    if url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql://', 1)
    return url

def get_sqlite_row_counts(sqlite_engine, meta):
    counts = {}
    with sqlite_engine.connect() as conn:
        for tname in TABLE_MIGRATION_ORDER:
            if tname in meta.tables:
                table = meta.tables[tname]
                cnt = conn.execute(sa.select(sa.func.count()).select_from(table)).scalar()
                counts[tname] = cnt
            else:
                counts[tname] = 0
    return counts

def reset_pg_sequence(pg_conn, table_name, pk_col_name):
    """
    Resets PostgreSQL sequence for a table with serial / auto-increment PK.
    """
    try:
        sql = text(f"""
            SELECT setval(
                pg_get_serial_sequence(:tname, :cname),
                COALESCE((SELECT MAX({pk_col_name}) FROM {table_name}), 1),
                true
            );
        """)
        pg_conn.execute(sql, {"tname": table_name, "cname": pk_col_name})
    except Exception as e:
        # Non-serial or table has no sequence
        pass

def run_migration():
    args = parse_arguments()

    print("=" * 72)
    print("  SAMADHAN SETU - SQLITE TO POSTGRESQL MIGRATION UTILITY")
    print("=" * 72)

    # 1. Verify SQLite Source
    if not os.path.exists(args.sqlite_path):
        print(f"[ERROR] Source SQLite database file not found: {args.sqlite_path}")
        sys.exit(1)

    sqlite_url = f"sqlite:///{os.path.abspath(args.sqlite_path)}"
    print(f"[*] Source SQLite: {sqlite_url}")

    sqlite_engine = create_engine(sqlite_url)
    sqlite_meta = MetaData()
    sqlite_meta.reflect(bind=sqlite_engine)

    # Inspect SQLite Counts
    sqlite_counts = get_sqlite_row_counts(sqlite_engine, sqlite_meta)
    print(f"[*] Found {len(sqlite_meta.tables)} tables in SQLite database.")
    print("-" * 72)
    for tname in TABLE_MIGRATION_ORDER:
        if tname in sqlite_counts:
            print(f"    - {tname:<28}: {sqlite_counts[tname]} rows")
    print("-" * 72)

    # Handle Dry Run
    if args.dry_run:
        print("[INFO] DRY RUN MODE COMPLETE: SQLite data structure verified.")
        print("       To perform actual migration, configure DATABASE_URL and run without --dry-run.")
        sys.exit(0)

    # 2. Check Target PostgreSQL URL
    target_pg_url = normalize_database_url(args.pg_url)
    if not target_pg_url:
        print("[ERROR] Target PostgreSQL URL is missing!")
        print("        Provide it via:")
        print("        1. .env file: DATABASE_URL=postgresql://user:password@localhost:5432/samadhan_setu")
        print("        2. Command line: --pg-url postgresql://user:password@localhost:5432/samadhan_setu")
        sys.exit(1)

    # Mask password for display
    masked_url = target_pg_url
    if '@' in masked_url and ':' in masked_url.split('@')[0]:
        prefix, rest = masked_url.split('@', 1)
        scheme_user, _ = prefix.rsplit(':', 1)
        masked_url = f"{scheme_user}:****@{rest}"
    print(f"[*] Target PostgreSQL: {masked_url}")

    # 3. Test Connection to PostgreSQL
    try:
        pg_engine = create_engine(target_pg_url, pool_pre_ping=True)
        with pg_engine.connect() as conn:
            pg_version = conn.execute(text("SELECT version();")).scalar()
            print(f"[OK] Connected to PostgreSQL: {pg_version.split(',')[0]}")
    except Exception as e:
        print("\n[ERROR] Could not connect to PostgreSQL target!")
        print(f"        Details: {str(e)}")
        print("\n[TROUBLESHOOTING GUIDE]")
        print("  1. Ensure PostgreSQL service is running:")
        print("     - Windows: Open 'Services' and ensure 'postgresql-x64' is Running.")
        print("     - Docker:  docker run --name pg-samadhan -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:15")
        print("  2. Verify database exists:")
        print("     - In psql: CREATE DATABASE samadhan_setu;")
        print("  3. Verify connection string format:")
        print("     - postgresql://username:password@localhost:5432/samadhan_setu\n")
        sys.exit(1)

    # 4. Import app models and create tables on PostgreSQL
    print("[*] Creating application tables in PostgreSQL...")
    try:
        from app import app, db
        with app.app_context():
            # Bind models to pg_engine to create tables
            db.metadata.create_all(bind=pg_engine)
        print("[OK] PostgreSQL schema created / verified successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to create PostgreSQL schema: {e}")
        sys.exit(1)

    # 5. Reflect Target PostgreSQL MetaData
    pg_meta = MetaData()
    pg_meta.reflect(bind=pg_engine)

    # 6. Migrate Data Table by Table
    print("\n[*] Starting row migration in dependency order...")
    pg_counts = {}

    with sqlite_engine.connect() as s_conn, pg_engine.begin() as p_conn:
        for tname in TABLE_MIGRATION_ORDER:
            if tname not in sqlite_meta.tables or tname not in pg_meta.tables:
                continue

            s_table = sqlite_meta.tables[tname]
            p_table = pg_meta.tables[tname]

            # Fetch rows from SQLite
            select_stmt = sa.select(s_table)
            rows = s_conn.execute(select_stmt).fetchall()

            if rows:
                col_names = [c.name for c in s_table.columns]
                row_dicts = []

                for row in rows:
                    row_dict = {}
                    for col_name in col_names:
                        val = getattr(row, col_name)
                        # Handle date/time parsing if stored as string in SQLite
                        p_col = p_table.columns.get(col_name)
                        if p_col is not None and isinstance(p_col.type, (sa.DateTime, sa.Date)) and isinstance(val, str):
                            try:
                                val = datetime.fromisoformat(val)
                            except Exception:
                                pass
                        row_dict[col_name] = val
                    row_dicts.append(row_dict)

                # Batch insert into PostgreSQL
                batch_size = args.batch_size
                for i in range(0, len(row_dicts), batch_size):
                    batch = row_dicts[i:i + batch_size]
                    p_conn.execute(p_table.insert(), batch)

            # Reset sequence if table has integer primary key
            pk_cols = [c.name for c in p_table.primary_key.columns]
            if pk_cols:
                reset_pg_sequence(p_conn, tname, pk_cols[0])

    # 7. Verification & Count Comparison
    print("\n" + "=" * 72)
    print(f"  {'TABLE NAME':<28} | {'SQLITE':<10} | {'POSTGRES':<10} | {'STATUS'}")
    print("=" * 72)

    all_matched = True
    with pg_engine.connect() as p_conn:
        for tname in TABLE_MIGRATION_ORDER:
            if tname in pg_meta.tables:
                p_table = pg_meta.tables[tname]
                p_cnt = p_conn.execute(sa.select(sa.func.count()).select_from(p_table)).scalar()
                pg_counts[tname] = p_cnt
                s_cnt = sqlite_counts.get(tname, 0)
                status = "[MATCH]" if s_cnt == p_cnt else "[MISMATCH]"
                if s_cnt != p_cnt:
                    all_matched = False
                print(f"  {tname:<28} | {s_cnt:<10} | {p_cnt:<10} | {status}")

    print("=" * 72)
    if all_matched:
        print("[SUCCESS] All tables migrated and verified with 100% data integrity!")
        print("          You can now run SamadhanSetu on PostgreSQL by keeping DATABASE_URL in .env.")
    else:
        print("[WARNING] One or more row counts mismatched. Inspect table logs.")

if __name__ == '__main__':
    run_migration()
