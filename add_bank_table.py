import sqlite3
import os
from datetime import datetime

# Get the path to the SQLite database
db_path = os.path.join('instance', 'ledgerbook.sqlite3')

# SQL to create the client_bank table
create_table_sql = '''
CREATE TABLE IF NOT EXISTS client_bank (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    bank_name TEXT NOT NULL,
    account_name TEXT NOT NULL,
    account_number TEXT NOT NULL,
    branch TEXT,
    location TEXT,
    routing_number TEXT,
    is_primary BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES client (id) ON DELETE CASCADE
);
'''

def run_migration():
    print(f"Checking for database at {db_path}...")
    
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        return False
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='client_bank';")
        if cursor.fetchone():
            print("ClientBank table already exists.")
            conn.close()
            return True
        
        # Create the table
        print("Creating client_bank table...")
        cursor.execute(create_table_sql)
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        print("Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting migration process...")
    success = run_migration()
    print(f"Migration {'successful' if success else 'failed'}")
    
    # Check if table exists
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='client_bank';")
        result = cursor.fetchone()
        print(f"Verified table exists: {bool(result)}")
        conn.close()
    except Exception as e:
        print(f"Error verifying table: {str(e)}") 