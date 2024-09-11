import json
import uuid
from sqLite import cursor, connection

def upsert_data_in_node_detail(miner_id, node_value):
    """Inserts or updates data in the node_detail table based on miner_id and IP."""
    try:
        print("Upserting data in node_detail table...")
        print("Node value...", node_value)
        # Extracting the node details
        node_data = node_value[miner_id][0]
        ip = node_data['ip']
        name = node_data['name']
        status = node_data['status']
        hotkey = node_data['hotkey']
        certificate = node_data['certificate']
        usage_port = node_data['usage_port']
        port = node_data['port']
        
        if ip is None:
            cursor.execute("SELECT * FROM node_detail WHERE ip IS NULL AND miner_id = ?", (miner_id,))
        else:
            cursor.execute("SELECT * FROM node_detail WHERE ip = ? AND miner_id = ?", (ip, miner_id))
        row = cursor.fetchone()
        print("Node_detail Row...", row)
        # If an entry already exists for the given IP and miner_id, return the existing row
        if row:
            print("Entry already exists for the given IP and miner_id. No update performed...")
            return row  # Return the existing row
        # Now check if there's an entry where ip is NULL and the miner_id is the same
        cursor.execute("SELECT * FROM node_detail WHERE ip IS NULL AND miner_id = ?", (miner_id,))
        null_ip_row = cursor.fetchone()
        # If an entry with ip=NULL exists for the miner_id, delete it
        if null_ip_row:
            print(f"Deleting entry with ip=NULL for miner_id={miner_id}")
            cursor.execute("DELETE FROM node_detail WHERE ip IS NULL AND miner_id = ?", (miner_id,))
            connection.commit()
        # Insert the new data
        unique_id = str(uuid.uuid4())
        query = """ 
            INSERT INTO node_detail (id, name, status, ip, port, usage_port, miner_id, hotkey, certificate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        cursor.execute(query, (unique_id, name, status, ip, port, usage_port, miner_id, hotkey, certificate))
        connection.commit()
        # Retrieve and return the inserted row
        cursor.execute("SELECT * FROM node_detail WHERE id = ?", (unique_id,))
        inserted_row = cursor.fetchone()
        print("Data inserted in node_detail table...", inserted_row)
        return inserted_row
        
    except Exception as e:
        print("XX-Error in upsert_data_in_node_detail-XX", e)
        return None

def get_data_in_node_detail(miner_id, ip):
    """Fetches a single entry from the node_detail table by miner_id."""
    try:
        print("Get data in node_detail table...")  

        cursor.execute("SELECT * FROM node_detail WHERE miner_id = ? AND ip = ?", (miner_id, ip))
        row = cursor.fetchone()        
        return row
    
    except Exception as e:
        print("**-- Error in get_data_in_node_detail --**", e)
        return None

def delete_data_in_node_detail(miner_id):
    """Deletes a specific entry in the node_detail table based on miner_id."""
    try:
        print("Deleting data in node_detail table...")        
        print(f"::miner_id:: {type(miner_id)}")

        # Delete the row where id matches the provided miner_id
        cursor.execute("DELETE FROM node_detail WHERE id = ?", (miner_id,))
        
        # Commit the transaction to ensure the delete is saved
        connection.commit()

        # Check if the row was successfully deleted by trying to fetch it
        cursor.execute("SELECT * FROM node_detail WHERE id = ?", (miner_id,))
        row = cursor.fetchone()

        if row is None:
            print(f"::Row with miner_id {miner_id} successfully deleted::")
        else:
            print(f"::Row with miner_id {miner_id} still exists::")
        
    except Exception as e:
        print("**-- Error in delete_data_in_node_detail --**", e)
        connection.rollback()  # Rollback in case of an error

def update_data_in_node_detail(miner_id, node_value):
    """Updates a specific entry in the node_detail table based on miner_id."""
    try:
        print("Updating data in node_detail table...")        
        print(f"::miner_id:: {type(miner_id)}")

        # Update the row where id matches the provided miner_id
        cursor.execute("UPDATE node_detail SET node = ? WHERE id = ?", (json.dumps(node_value), miner_id))
        
        # Commit the transaction to ensure the update is saved
        connection.commit()
        print("Data updated in node_detail table...")

        # Check if the row was successfully updated by trying to fetch it
        cursor.execute("SELECT * FROM node_detail WHERE id = ?", (miner_id,))
        row = cursor.fetchone()

        return row
        
    except Exception as e:
        print("**-- Error in update_data_in_node_detail --**", e)
        connection.rollback()  # Rollback in case of an error

def get_all_data_in_node_detail():
    """Fetches all entries from the node_detail table."""
    try:
        print("Get all data in node_detail table...")

        cursor.execute("SELECT * FROM node_detail")
        rows = cursor.fetchall()
        return rows
    
    except Exception as e:
        print("XX - Error in get_all_data_in_node_detail - XX", e)
        return None

def update_certificate_in_node_detail(miner_id, ip, certificate):
    """Updates a specific entry in the node_detail table based on miner_id."""
    try:
        print("Updating certificate in node_detail table...")        
        print(f"::miner_id:: {type(miner_id)}")

        # Update the row where id matches the provided miner_id
        cursor.execute("UPDATE node_detail SET certificate = ? WHERE ip = ? AND miner_id = ?", (certificate, ip, miner_id))
        
        # Commit the transaction to ensure the update is saved
        connection.commit()
        print("Certificate updated in node_detail table...")

        # Check if the row was successfully updated by trying to fetch it
        cursor.execute("SELECT * FROM node_detail WHERE id = ?", (miner_id,))
        row = cursor.fetchone()

        return row
    
    except Exception as e:
        print("**-- Error in update_certificate_in_node_detail --**", e)
        connection.rollback()  # Rollback in case of an error

def get_node_detail_by_ip(ip):
    """Fetches a single entry from the node_detail table by IP."""
    try:
        print("Get node detail by IP...")
        cursor.execute("SELECT * FROM node_detail WHERE ip = ?", (ip,))
        row = cursor.fetchone()
        return row
    except Exception as e:
        print("XX - Error in get_node_detail_by_ip - XX", e)
        return None