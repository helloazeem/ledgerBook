import os
import sys
import time
import sqlite3
import shutil

def main():
    # Path to the database file
    instance_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
    db_path = os.path.join(instance_dir, "ledgerbook.sqlite3")
    
    # Check if database file exists
    if os.path.exists(db_path):
        print(f"Database found at: {db_path}")
        
        # Try to connect to verify we can access it
        try:
            conn = sqlite3.connect(db_path)
            conn.close()
            print("Successfully connected to database")
            
            # Try to delete the file
            try:
                os.remove(db_path)
                print(f"Successfully deleted the database file")
            except Exception as e:
                print(f"Error deleting database file: {e}")
                print("\nAttempting forceful deletion in Windows...")
                
                # For Windows systems
                if os.name == 'nt':
                    try:
                        # Try to force close any connections
                        os.system(f'taskkill /F /IM python.exe /T')
                        time.sleep(1)
                        
                        # Try to delete again
                        if os.path.exists(db_path):
                            os.remove(db_path)
                            print("Successfully deleted database after force closing connections")
                    except Exception as e:
                        print(f"Error with force deletion: {e}")
                        print("\nPlease manually stop any running Flask applications and delete the file at:")
                        print(db_path)
        except Exception as e:
            print(f"Error connecting to database: {e}")
            print("This likely means the database is locked by another process")
            print("Please close any running Flask applications and try again")
    else:
        print(f"No database found at: {db_path}")
    
    # Clean up instance directory
    if os.path.exists(instance_dir):
        for filename in os.listdir(instance_dir):
            filepath = os.path.join(instance_dir, filename)
            try:
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    print(f"Deleted file: {filename}")
            except Exception as e:
                print(f"Error deleting {filename}: {e}")
    
    print("\nCleanup complete. Please run python recreate_db.py to create a fresh database.")

if __name__ == "__main__":
    main() 