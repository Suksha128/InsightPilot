import sqlite3
import json
import re
import time

import pandas as pd
from google import genai
from vanna.legacy.chromadb import ChromaDB_VectorStore

MODEL = "gemini-2.0-flash"


# ---------------------------------------------------------------------------
# Custom Gemini LLM wrapper (replaces broken vanna.legacy.google)
# ---------------------------------------------------------------------------

class CustomGeminiChat:
    def __init__(self, config=None):
        config = config or {}
        self.api_key = config.get("api_key")
        self.model_name = config.get("model", MODEL)
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    def system_message(self, message: str) -> dict:
        return {"role": "system", "content": message}

    def user_message(self, message: str) -> dict:
        return {"role": "user", "content": message}

    def assistant_message(self, message: str) -> dict:
        return {"role": "assistant", "content": message}

    def submit_prompt(self, prompt, **kwargs) -> str:
        if not self.client:
            return "Error: Gemini API key is missing."

        if isinstance(prompt, str):
            contents = prompt
        else:
            # Flatten chat-style list into a single string
            contents = "\n".join(
                f"{msg['role'].upper()}: {msg['content']}" for msg in prompt
            )

        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                )
                return response.text
            except Exception as e:
                if "429" in str(e):
                    if attempt < 2:
                        time.sleep(15)   # silent retry
                        continue
                    # Exhausted retries — return safe fallback SQL
                    return "SELECT 'API rate limit reached. Please wait a moment.' AS message;"
                return str(e)
        return ""


# ---------------------------------------------------------------------------
# Vanna subclass
# ---------------------------------------------------------------------------

class MyVanna(CustomGeminiChat, ChromaDB_VectorStore):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        CustomGeminiChat.__init__(self, config=config)


# ---------------------------------------------------------------------------
# Factory — returns a trained, read-only Vanna instance
# ---------------------------------------------------------------------------

def get_vanna_instance(api_key: str) -> MyVanna:
    vn = MyVanna(config={"api_key": api_key, "model": MODEL})

    # Train on schema once (skipped if training data already exists)
    try:
        if len(vn.get_training_data()) == 0:
            conn_train = sqlite3.connect("business_data.db")
            ddl_rows = pd.read_sql_query(
                "SELECT sql FROM sqlite_master "
                "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%'",
                conn_train,
            )
            for ddl in ddl_rows["sql"]:
                if ddl:
                    vn.train(ddl=ddl)
            conn_train.close()
    except Exception:
        pass

    # Enforce read-only execution
    def run_sql_readonly(sql: str) -> pd.DataFrame:
        conn = sqlite3.connect("file:business_data.db?mode=ro", uri=True)
        try:
            return pd.read_sql_query(sql, conn)
        finally:
            conn.close()

    vn.run_sql = run_sql_readonly
    return vn


# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------

DANGEROUS = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "GRANT", "REVOKE"]
AMBIGUOUS_TERMS = ["best", "top", "worst"]
CLARIFIERS = ["revenue", "sales", "margin", "orders", "frequency", "profit", "volume", "lifetime value"]


def detect_ambiguity(prompt: str):
    lower = prompt.lower()
    for term in AMBIGUOUS_TERMS:
        if re.search(rf"\b{term}\b", lower):
            if not any(c in lower for c in CLARIFIERS):
                return True, (
                    f"I see you asked about **'{term}'**. "
                    f"Could you clarify the metric? (e.g. by revenue, frequency, or margin?)"
                )
    return False, ""


def validate_sql(sql: str):
    upper = sql.upper()
    for word in DANGEROUS:
        if re.search(rf"\b{word}\b", upper):
            return False, f"🚫 Guardrail: keyword **{word}** is not allowed. Only SELECT queries are permitted."
    # Append LIMIT if missing (strip trailing semicolon first)
    if "LIMIT" not in upper:
        sql = sql.strip().rstrip(";") + "\nLIMIT 1000"
    return True, sql


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def check_cache(prompt: str):
    try:
        conn = sqlite3.connect("telemetry.db")
        cur = conn.cursor()
        cur.execute("SELECT generated_sql FROM prompt_cache WHERE prompt = ?", (prompt,))
        row = cur.fetchone()
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
# Telemetry / logging
# ---------------------------------------------------------------------------

def log_query(prompt: str, sql: str, latency: float, status: str, error_msg: str = "") -> int:
    try:
        conn = sqlite3.connect("telemetry.db")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO logs (prompt, generated_sql, latency, status, error_message) "
            "VALUES (?, ?, ?, ?, ?)",
            (prompt, sql, latency, status, error_msg),
        )
        log_id = cur.lastrowid
        conn.commit()
        conn.close()
        return log_id
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

def save_insight(title: str, prompt: str, sql: str, summary: str):
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
        df = pd.read_sql_query("SELECT * FROM saved_insights ORDER BY timestamp DESC", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Combined AI: business summary + follow-up questions (single API call)
# ---------------------------------------------------------------------------

def generate_insights_and_followups(prompt: str, df: pd.DataFrame, api_key: str) -> dict:
    if df is None or df.empty:
        return {
            "summary": "No data was returned for this query.",
            "followups": ["Try another category", "Show monthly trend", "Check customer segments"],
        }

    client = genai.Client(api_key=api_key)
    markdown_data = df.head(50).to_markdown()

    prompt_text = f"""
The user asked: '{prompt}'
Data (first 50 rows):
{markdown_data}

Tasks:
1. Write a short, actionable business summary (3 sentences max).
2. Suggest exactly 3 short follow-up questions to dig deeper.

Return ONLY valid JSON in this exact shape:
{{
  "summary": "...",
  "followups": ["...", "...", "..."]
}}
"""

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt_text,
                config={"response_mime_type": "application/json"},
            )
            text = response.text.strip()
            # Strip accidental markdown fences
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            result = json.loads(text)
            return result
        except Exception as e:
            if "429" in str(e):
                if attempt < 2:
                    time.sleep(15)
                    continue
                return {
                    "summary": "⏳ Rate limit reached — please wait ~1 minute and ask again.",
                    "followups": ["Break down by category", "Show monthly trend", "What are the top 5?"],
                }
            return {
                "summary": f"Insight generation failed: {e}",
                "followups": ["Break down by category", "Show monthly trend", "What are the top 5?"],
            }

    return {
        "summary": "Could not generate insight after retries.",
        "followups": ["Break down by category", "Show monthly trend", "What are the top 5?"],
    }
