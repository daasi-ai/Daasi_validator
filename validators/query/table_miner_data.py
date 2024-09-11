from sqLite import cursor, connection
import uuid

def miner_data_get_one(miner_id):
    """Fetches a single entry from the miner_data table by miner_id."""
    try:
        print("Fetching single data from miner_data...")
        cursor.execute("SELECT * FROM miner_data WHERE miner_id = ?", (miner_id,))
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        print("**-- Error in get_data_from_miner_data --**", e)
        return None

def miner_data_get_all():
    """Fetches all entries from the miner_data table."""
    try:
        print("Fetching all miner data...")
        cursor.execute("SELECT * FROM miner_data")
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        print("**-- Error in get_data_from_miner_data --**", e)
        return None

def insert_data_in_miner_data(miner_id, miner_value):
    """Inserts data into the miner_data table, replacing existing entries for the same miner_id."""
    try:
        print("Inserting data in miner_data table...")
        
        # Unpack the miner_value tuple
        miner_id, cpu_score, ram_score, disk_score, openai_tokens, groq_tokens, claude_tokens, gemini_tokens, total_requests, zero_value_entries = miner_value
        
        # Generate a new UUID for the id field
        unique_id = str(uuid.uuid4())
        
        # Check if the miner_id already exists
        query_check = "SELECT id FROM miner_data WHERE miner_id = ?"
        cursor.execute(query_check, (miner_id,))
        existing_row = cursor.fetchone()

        if existing_row:
            # Delete the old record if it exists
            delete_query = "DELETE FROM miner_data WHERE miner_id = ?"
            cursor.execute(delete_query, (miner_id,))
            print(f"Existing record for miner_id {miner_id} deleted.")

        # Insert the new data
        query_insert = """INSERT INTO miner_data (
            id, miner_id, cpu_score, ram_score, disk_score, 
            openai_tokens, groq_tokens, claude_tokens, gemini_tokens, 
            total_requests, zero_value_entries
        )
        VALUES (
            ?, ?, ?, ?, ?, 
            ?, ?, ?, ?, 
            ?, ?
        );"""
        cursor.execute(query_insert, (unique_id, miner_id, cpu_score, ram_score, disk_score, openai_tokens, groq_tokens, claude_tokens, gemini_tokens, total_requests, zero_value_entries))
        
        # Commit the transaction
        connection.commit()
        
        # Retrieve and return the inserted row
        cursor.execute("SELECT * FROM miner_data WHERE id = ?", (unique_id,))
        row = cursor.fetchone()

        print("Data inserted in miner_data table...", row)
        return row
        
    except Exception as e:
        print("**-- Error in insert_data_in_miner_data --**", e)
        return None