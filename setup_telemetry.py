import sqlite3

def create_telemetry_db(db_name="telemetry.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Create logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            prompt TEXT,
            generated_sql TEXT,
            latency REAL,
            status TEXT,
            error_message TEXT
        )
    ''')

    # Create feedback table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id INTEGER,
            feedback_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(log_id) REFERENCES logs(log_id)
        )
    ''')

    # Create cache table (prompt -> sql)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prompt_cache (
            prompt TEXT PRIMARY KEY,
            generated_sql TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create saved insights table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_insights (
            insight_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            prompt TEXT,
            generated_sql TEXT,
            business_summary TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    print("Telemetry database created successfully.")
    conn.close()

if __name__ == "__main__":
    create_telemetry_db()
