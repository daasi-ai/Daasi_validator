from sqLite import cursor, connection
import uuid

def insert_data_in_normalized_score(score_details):
    """Inserts or updates a score in the normalized_scores table."""
    try:
        # Generate a new UUID for the id field
        unique_id = str(uuid.uuid4())
        
        # Unpack the score_details tuple
        miner_id, score, rank = score_details
        
        # Check if the miner_id already exists
        query_check = "SELECT id FROM normalized_scores WHERE miner_id = ?"
        cursor.execute(query_check, (miner_id,))
        existing_row = cursor.fetchone()

        if existing_row:
            # Delete the old record if it exists
            delete_query = "DELETE FROM normalized_scores WHERE miner_id = ?"
            cursor.execute(delete_query, (miner_id,))
            print(f"Existing record for miner_id {miner_id} deleted.")

        # Insert the new data
        query_insert = """
            INSERT INTO normalized_scores (id, miner_id, score, rank)
            VALUES (?, ?, ?, ?);
        """
        cursor.execute(query_insert, (unique_id, miner_id, score, rank))
        
        # Commit the transaction
        connection.commit()
        
        print("Data inserted in normalized_scores table...")
        
    except Exception as e:
        print("XX-Error in insert_data_in_normalized_score-XX", e)

def get_a_data_from_normalized_score(miner_id):
    """Fetches a single entry from the normalized_scores table by miner_id."""
    try:
        cursor.execute("SELECT * FROM normalized_scores WHERE miner_id = ?", (miner_id,))
        row = cursor.fetchone()
        return row
    except Exception as e:
        print("XX-Error in get_a_data_from_normalized_score-XX", e)
        return None

def get_all_data_from_normalized_score():
    """Fetches all entries from the normalized_scores table."""
    try:
        cursor.execute("SELECT * FROM normalized_scores")
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        print("XX-Error in get_all_data_from_normalized_score-XX", e)
        return None
