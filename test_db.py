from app import app, db
import sqlalchemy as sa
from sqlalchemy import inspect, text
import sqlite3
import os

# Database file path
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'ledgerbook.sqlite3')

# Run within app context
with app.app_context():
    inspector = inspect(db.engine)
    
    # Print all tables
    print("Database Tables:")
    print("===============")
    tables = inspector.get_table_names()
    for table in tables:
        print(f"\nTable: {table}")
        print("Columns:")
        for column in inspector.get_columns(table):
            print(f"  - {column['name']} ({column['type']})")
        
        print("Primary Key:", inspector.get_pk_constraint(table))
        print("Foreign Keys:")
        for fk in inspector.get_foreign_keys(table):
            print(f"  - {fk}")
    
    # Check if transaction table has the correct structure
    transaction_columns = [col['name'] for col in inspector.get_columns('transaction')]
    
    if 'invoice_number' not in transaction_columns:
        print("\n!!! PROBLEM: 'invoice_number' column is missing from transaction table !!!")
        
        # Try to fix the transaction table
        print("\nAttempting to fix transaction table structure...")
        
        try:
            # Use direct SQLite connection for more control
            # Note: This approach is for SQLite only
            print("Connecting to SQLite database directly...")
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Check current structure 
                cursor.execute('PRAGMA table_info("transaction");')
                cols = cursor.fetchall()
                print("\nCurrent transaction table columns:")
                for col in cols:
                    print(f"  - {col[1]} ({col[2]})")
                
                # Add the missing invoice_number column
                print("\nAdding missing invoice_number column...")
                cursor.execute('ALTER TABLE "transaction" ADD COLUMN invoice_number VARCHAR(20);')
                conn.commit()
                
                # Verify the column was added
                cursor.execute('PRAGMA table_info("transaction");')
                cols = cursor.fetchall()
                print("\nUpdated transaction table columns:")
                for col in cols:
                    print(f"  - {col[1]} ({col[2]})")
                
                print("\nFix completed successfully!")
        except Exception as e:
            print(f"\nError fixing database: {e}") 