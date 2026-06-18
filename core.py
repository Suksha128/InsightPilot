import sqlite3
import json
import re
import time

import duckdb
import pandas as pd
from groq import Groq
from vanna.legacy.chromadb import ChromaDB_VectorStore
from data_manager import DUCK_PATH, get_ddl_statements

MODEL = "llama3-8b-8192"   # Faster, lighter model to avoid Groq free-tier rate limits


# ---------------------------------------------------------------------------
# Custom Groq LLM wrapper for Vanna
# ---------------------------------------------------------------------------

class CustomGroqChat:
    def __init__(self, config=None):
        config = config or {}
        self.api_key   = config.get("api_key")
        self.model_name = config.get("model", MODEL)
        self.client    = Groq(api_key=self.api_key) if self.api_key else None

    def system_message(self, message: str) -> dict:
        # Enforce strict DuckDB dialect and GROUP BY rules
        duckdb_rules = (
            "\n\nCRITICAL DUCKDB SQL RULES:\n"
            "1. You are generating SQL for DuckDB.\n"
            "2. If you use GROUP BY, EVERY non-aggregated column in the SELECT list MUST appear in the GROUP BY list.\n"
            "3. Do NOT select unaggregated columns (e.g. table.deal_value) if you are not grouping by them. Use ANY_VALUE(col) or SUM(col) instead.\n"
            "4. Always use proper Postgres/DuckDB syntax.\n"
        )
        return {"role": "system", "content": message + duckdb_rules}

    def user_message(self, message: str) -> dict:
        return {"role": "user", "content": message}

    def assistant_message(self, message: str) -> dict:
        return {"role": "assistant", "content": message}

    def submit_prompt(self, prompt, **kwargs) -> str:
        if not self.client:
            return "Error: Groq API key is missing."

        # Normalise prompt into a messages list
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            # Vanna passes a list of role dicts; map 'system' role
            messages = []
            for msg in prompt:
                role = msg.get("role", "user")
                if role not in ("system", "user", "assistant"):
                    role = "user"
                messages.append({"role": role, "content": msg["content"]})

        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0,
                    max_tokens=2048,
                )
                return response.choices[0].message.content
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    if attempt < 2:
                        time.sleep(15)
                        continue
                    return "SELECT 'Rate limit reached. Please wait a moment.' AS message;"
                return str(e)
        return ""


# ---------------------------------------------------------------------------
# Vanna subclass
# ---------------------------------------------------------------------------

class MyVanna(CustomGroqChat, ChromaDB_VectorStore):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        CustomGroqChat.__init__(self, config=config)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_vanna_instance(api_key: str) -> MyVanna:
    vn = MyVanna(config={"api_key": api_key, "model": MODEL})

    # Train on DuckDB schema (always refresh so uploads are reflected)
    try:
        old = vn.get_training_data()
        if old is not None and len(old) > 0:
            for tid in old["id"].tolist():
                try:
                    vn.remove_training_data(id=tid)
                except Exception:
                    pass
    except Exception:
        pass

    for ddl in get_ddl_statements():
        try:
            vn.train(ddl=ddl)
        except Exception:
            pass

    # Read-only DuckDB runner
    def run_sql_duckdb(sql: str) -> pd.DataFrame:
        con = duckdb.connect(DUCK_PATH, read_only=True)
        try:
            return con.execute(sql).df()
        finally:
            con.close()

    vn.run_sql = run_sql_duckdb
    return vn


# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------

DANGEROUS    = ["DROP","DELETE","UPDATE","INSERT","ALTER","TRUNCATE","GRANT","REVOKE"]
AMBIGUOUS    = ["best","top","worst"]
CLARIFIERS   = ["revenue","sales","margin","orders","frequency","profit","volume","lifetime value"]


def detect_ambiguity(prompt: str):
    lower = prompt.lower()
    for term in AMBIGUOUS:
        if re.search(rf"\b{term}\b", lower):
            if not any(c in lower for c in CLARIFIERS):
                return True, (
                    f"I see you asked about **'{term}'**. "
                    "Could you clarify the metric? (e.g. by revenue, frequency, or margin?)"
                )
    return False, ""


def validate_sql(sql: str):
    upper = sql.upper()
    for word in DANGEROUS:
        if re.search(rf"\b{word}\b", upper):
            return False, f"Keyword **{word}** is not permitted. Only SELECT queries are allowed."
    if "LIMIT" not in upper:
        sql = sql.strip().rstrip(";") + "\nLIMIT 1000"
    return True, sql


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def check_cache(prompt: str):
    try:
        conn = sqlite3.connect("telemetry.db")
        cur  = conn.cursor()
        cur.execute("SELECT generated_sql FROM prompt_cache WHERE prompt = ?", (prompt,))
        row  = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def save_cache(prompt: str, sql: str):
    try:
        conn = sqlite3.connect("telemetry.db")
        conn.execute(
            "INSERT OR REPLACE INTO prompt_cache (prompt, generated_sql) VALUES (?, ?)",
            (prompt, sql),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

def log_query(prompt, sql, latency, status, error_msg="") -> int:
    try:
        conn = sqlite3.connect("telemetry.db")
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO logs (prompt, generated_sql, latency, status, error_message) "
            "VALUES (?, ?, ?, ?, ?)",
            (prompt, sql, latency, status, error_msg),
        )
        lid = cur.lastrowid
        conn.commit()
        conn.close()
        return lid
    except Exception:
        return -1


def log_feedback(log_id: int, feedback_type: str):
    try:
        conn = sqlite3.connect("telemetry.db")
        conn.execute(
            "INSERT INTO feedback (log_id, feedback_type) VALUES (?, ?)",
            (log_id, feedback_type),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Saved insights
# ---------------------------------------------------------------------------

def save_insight(title, prompt, sql, summary):
    try:
        conn = sqlite3.connect("telemetry.db")
        conn.execute(
            "INSERT INTO saved_insights (title, prompt, generated_sql, business_summary) "
            "VALUES (?, ?, ?, ?)",
            (title, prompt, sql, summary),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_saved_insights() -> pd.DataFrame:
    try:
        conn = sqlite3.connect("telemetry.db")
        df   = pd.read_sql_query("SELECT * FROM saved_insights ORDER BY timestamp DESC", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def delete_insight(insight_id: int):
    try:
        conn = sqlite3.connect("telemetry.db")
        cur  = conn.cursor()
        cur.execute("DELETE FROM saved_insights WHERE id = ?", (insight_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Combined AI insight + follow-ups  (single Groq call)
# ---------------------------------------------------------------------------

def generate_insights_and_followups(prompt: str, df: pd.DataFrame, api_key: str) -> dict:
    if df is None or df.empty:
        return {
            "summary":   "No data was returned for this query.",
            "followups": ["Try another category", "Show monthly trend", "Check customer segments"],
        }

    client       = Groq(api_key=api_key)
    markdown_data = df.head(50).to_markdown()

    system_msg = (
        "You are a concise business analyst. "
        "Always respond with valid JSON only — no markdown fences, no extra text."
    )
    user_msg = f"""
The user asked: '{prompt}'
Data (first 50 rows):
{markdown_data}

Return ONLY this JSON:
{{
  "summary": "2-3 sentence actionable business insight",
  "followups": ["follow-up 1", "follow-up 2", "follow-up 3"]
}}
"""

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system",  "content": system_msg},
                    {"role": "user",    "content": user_msg},
                ],
                temperature=0,
                max_tokens=512,
                response_format={"type": "json_object"},
            )
            text   = response.choices[0].message.content.strip()
            result = json.loads(text)
            return result
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                if attempt < 2:
                    time.sleep(15)
                    continue
                return {
                    "summary":   "⏳ Rate limit reached — please wait a moment and ask again.",
                    "followups": ["Break down by category", "Show monthly trend", "What are the top 5?"],
                }
            return {
                "summary":   f"Insight generation failed: {e}",
                "followups": ["Break down by category", "Show monthly trend", "What are the top 5?"],
            }

    return {
        "summary":   "Could not generate insight after retries.",
        "followups": ["Break down by category", "Show monthly trend", "What are the top 5?"],
    }
