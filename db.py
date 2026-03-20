"""F1 Database Schema & Helper Functions"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'f1.db')

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initialize database with schema"""
    conn = get_conn()
    cursor = conn.cursor()
    
    # Races table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS races (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT,
            session_key INTEGER UNIQUE,
            country TEXT,
            circuit TEXT
        )
    ''')
    
    # Race results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS race_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_id INTEGER,
            position INTEGER,
            driver_code TEXT,
            driver_name TEXT,
            team TEXT,
            time_gap TEXT,
            points REAL,
            FOREIGN KEY (race_id) REFERENCES races (id)
        )
    ''')
    
    # Lap times table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lap_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_id INTEGER,
            driver_code TEXT,
            lap INTEGER,
            lap_time_ms INTEGER,
            timestamp TEXT,
            FOREIGN KEY (race_id) REFERENCES races (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized: {DB_PATH}")

if __name__ == '__main__':
    init_db()
