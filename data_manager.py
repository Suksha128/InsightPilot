"""
data_manager.py — upload, inspect, and manage business data via DuckDB.

DuckDB is the primary analytics engine. It handles:
  • CSV   — streamed via DuckDB's native reader (no size limit)
  • Parquet — queried in-place or ingested
  • Excel — loaded via pandas, then pushed to DuckDB
  • JSON  — loaded via pandas, then pushed to DuckDB
  • SQLite .db files — tables copied into DuckDB

All business data lives in business_data.duckdb
Telemetry / caching stays in telemetry.db (SQLite)
"""
import os
import io
import re
import sqlite3
import tempfile

import pandas as pd
import duckdb

DUCK_PATH   = "business_data.duckdb"
CHUNK_SIZE  = 100_000        # rows per pandas chunk for Excel/JSON
LARGE_CSV_THRESHOLD = 50     # MB — above this, use DuckDB native CSV reader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _duck() -> duckdb.DuckDBPyConnection:
    """Open a fresh DuckDB connection (thread-safe per-connection model)."""
    return duckdb.connect(DUCK_PATH)


def db_exists() -> bool:
    if not os.path.exists(DUCK_PATH):
        return False
    try:
        con = _duck()
        tables = con.execute("SHOW TABLES").fetchall()
        con.close()
        return len(tables) > 0
    except Exception:
        return False


def get_schema() -> dict:
    """Return {table_name: {columns, row_count}} for every table."""
    if not os.path.exists(DUCK_PATH):
        return {}
    schema = {}
    try:
        con = _duck()
        tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
        for t in tables:
            cols_raw  = con.execute(f"DESCRIBE '{t}'").fetchall()
            row_count = con.execute(f"SELECT COUNT(*) FROM '{t}'").fetchone()[0]
            schema[t] = {
                "columns":   [{"name": r[0], "type": r[1]} for r in cols_raw],
                "row_count": row_count,
            }
        con.close()
    except Exception:
        pass
    return schema


def get_ddl_statements() -> list[str]:
    """Return CREATE TABLE DDL strings for all tables (for Vanna training)."""
    if not os.path.exists(DUCK_PATH):
        return []
    ddls = []
    try:
        con = _duck()
        tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
        for t in tables:
            cols = con.execute(f"DESCRIBE '{t}'").fetchall()
            col_defs = ",\n  ".join(f'"{r[0]}" {r[1]}' for r in cols)
            ddls.append(f'CREATE TABLE "{t}" (\n  {col_defs}\n);')
        con.close()
    except Exception:
        pass
    return ddls


def get_db_size_mb() -> float:
    if not os.path.exists(DUCK_PATH):
        return 0.0
    return os.path.getsize(DUCK_PATH) / (1024 * 1024)


def preview_table(table_name: str, n: int = 200) -> pd.DataFrame:
    con = _duck()
    df  = con.execute(f"SELECT * FROM '{table_name}' LIMIT {n}").df()
    con.close()
    return df


def drop_table(table_name: str):
    con = _duck()
    con.execute(f"DROP TABLE IF EXISTS '{table_name}'")
    con.close()


def reset_database():
    if os.path.exists(DUCK_PATH):
        os.remove(DUCK_PATH)
    # Also clean up WAL files
    for ext in [".wal", ".tmp"]:
        p = DUCK_PATH + ext
        if os.path.exists(p):
            os.remove(p)


# ---------------------------------------------------------------------------
# Name sanitisation
# ---------------------------------------------------------------------------

def _clean_name(name: str) -> str:
    name = os.path.splitext(name)[0]
    name = re.sub(r"[^\w]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name.lower()[:60] or "data"


def _clean_cols(df: pd.DataFrame) -> pd.DataFrame:
    def fix(c):
        c = re.sub(r"[^\w]", "_", str(c).strip())
        c = re.sub(r"_+", "_", c).strip("_")
        return c.lower()[:60] or "col"
    df.columns = [fix(c) for c in df.columns]
    return df


# ---------------------------------------------------------------------------
# Core ingest
# ---------------------------------------------------------------------------

def ingest_file(uploaded_file, progress_cb=None) -> tuple[list[str], str]:
    """
    Ingest a Streamlit UploadedFile into DuckDB.
    Returns (list_of_table_names, error_string).
    progress_cb(fraction 0–1) is called as progress is made.
    """
    name   = uploaded_file.name
    ext    = os.path.splitext(name)[1].lower()
    size_mb = uploaded_file.size / (1024 * 1024)
    tables = []

    try:
        # ── Parquet — DuckDB reads it natively, fastest possible path ──────
        if ext == ".parquet":
            table_name = _clean_name(name)
            raw = uploaded_file.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".parquet") as tmp:
                tmp.write(raw)
                tmp_path = tmp.name
            if progress_cb: progress_cb(0.3)
            con = _duck()
            con.execute(f"CREATE OR REPLACE TABLE \"{table_name}\" AS SELECT * FROM read_parquet('{tmp_path}')")
            con.close()
            os.unlink(tmp_path)
            if progress_cb: progress_cb(1.0)
            tables.append(table_name)

        # ── CSV — use DuckDB native reader for large files ─────────────────
        elif ext == ".csv":
            table_name = _clean_name(name)
            raw = uploaded_file.read()
            if progress_cb: progress_cb(0.1)

            if size_mb > LARGE_CSV_THRESHOLD:
                # Write to temp file, let DuckDB read it directly
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                    tmp.write(raw)
                    tmp_path = tmp.name
                if progress_cb: progress_cb(0.4)
                con = _duck()
                con.execute(
                    f"CREATE OR REPLACE TABLE \"{table_name}\" AS "
                    f"SELECT * FROM read_csv_auto('{tmp_path}', header=true, null_padding=true)"
                )
                con.close()
                os.unlink(tmp_path)
            else:
                # Small CSV — pandas for clean column name handling
                buf   = io.BytesIO(raw)
                con   = _duck()
                first = True
                for chunk in pd.read_csv(buf, chunksize=CHUNK_SIZE, low_memory=False):
                    chunk = _clean_cols(chunk)
                    if first:
                        con.execute(f"CREATE OR REPLACE TABLE \"{table_name}\" AS SELECT * FROM chunk")
                        first = False
                    else:
                        con.execute(f"INSERT INTO \"{table_name}\" SELECT * FROM chunk")
                con.close()

            if progress_cb: progress_cb(1.0)
            tables.append(table_name)

        # ── Excel — each sheet → one table ────────────────────────────────
        elif ext in (".xlsx", ".xls"):
            raw = uploaded_file.read()
            buf = io.BytesIO(raw)
            xf  = pd.ExcelFile(buf)
            con = _duck()
            for i, sheet in enumerate(xf.sheet_names):
                table_name = _clean_name(sheet)
                df = pd.read_excel(xf, sheet_name=sheet, dtype=str)
                df = _clean_cols(df)
                con.execute(f"CREATE OR REPLACE TABLE \"{table_name}\" AS SELECT * FROM df")
                tables.append(table_name)
                if progress_cb: progress_cb((i + 1) / len(xf.sheet_names))
            con.close()

        # ── SQLite .db — copy all tables into DuckDB ───────────────────────
        elif ext in (".db", ".sqlite", ".sqlite3"):
            raw = uploaded_file.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
                tmp.write(raw)
                tmp_path = tmp.name

            try:
                src  = sqlite3.connect(tmp_path)
                cur  = src.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                src_tables = [r[0] for r in cur.fetchall()]
            except Exception:
                os.unlink(tmp_path)
                return [], "Not a valid SQLite database."

            con = _duck()
            for i, t in enumerate(src_tables):
                df = pd.read_sql_query(f"SELECT * FROM '{t}'", src)
                df = _clean_cols(df)
                table_name = _clean_name(t)
                con.execute(f"CREATE OR REPLACE TABLE \"{table_name}\" AS SELECT * FROM df")
                tables.append(table_name)
                if progress_cb: progress_cb((i + 1) / len(src_tables))
            src.close()
            con.close()
            os.unlink(tmp_path)

        # ── JSON ──────────────────────────────────────────────────────────
        elif ext == ".json":
            table_name = _clean_name(name)
            raw = uploaded_file.read()
            df  = pd.read_json(io.BytesIO(raw))
            df  = _clean_cols(df)
            con = _duck()
            con.execute(f"CREATE OR REPLACE TABLE \"{table_name}\" AS SELECT * FROM df")
            con.close()
            if progress_cb: progress_cb(1.0)
            tables.append(table_name)

        else:
            return [], f"Unsupported file type: {ext}"

        return tables, ""

    except Exception as e:
        return [], str(e)
