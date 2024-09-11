import sqlite3

connection = sqlite3.connect('local_database.db')
cursor = connection.cursor()


def create_node_detail_table():
    try:
        print("Creating Tables...")
        queries = [
            """
                CREATE TABLE IF NOT EXISTS node_detail (
                    id TEXT PRIMARY KEY,         -- Primary key, still mandatory
                    name TEXT,                   -- Nullable
                    status TEXT,                 -- Nullable
                    ip TEXT,                     -- Nullable
                    port INTEGER,                -- Nullable
                    usage_port INTEGER,          -- Nullable
                    miner_id INTEGER NOT NULL,    
                    hotkey TEXT,                 -- Nullable
                    certificate TEXT             -- Nullable
                );
            """,
            """
                CREATE TABLE IF NOT EXISTS miner_data (
                    id TEXT PRIMARY KEY,               -- Primary key, mandatory
                    miner_id INTEGER NOT NULL,         -- Nullable
                    cpu_score REAL,                    -- Nullable
                    ram_score REAL,                    -- Nullable
                    disk_score REAL,                   -- Nullable
                    openai_tokens INTEGER,             -- Nullable
                    groq_tokens INTEGER,               -- Nullable
                    claude_tokens INTEGER,             -- Nullable
                    gemini_tokens INTEGER,             -- Nullable
                    total_requests INTEGER,            -- Nullable
                    zero_value_entries INTEGER         -- Nullable
                );
            """,
            """
                CREATE TABLE IF NOT EXISTS normalized_scores (
                    id TEXT PRIMARY KEY,  
                    miner_id INTEGER NOT NULL,
                    score REAL NOT NULL,  
                    rank INTEGER NOT NULL
                );
            """
        ]
        # normalized_score
        for query in queries:
            cursor.execute(query)
        
        connection.commit()
    except Exception as e:
        print("**-- Error in docker_tool_info --**", e)
