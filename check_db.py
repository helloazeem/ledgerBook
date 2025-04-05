from app import app, db
from models import User, Client, Transaction, CompanySettings, Todo
import os
from sqlalchemy import inspect

def check_db_connection():
    try:
        with app.app_context():
            # Check SQLite database file exists
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            if os.path.exists(db_path):
                print(f"Database file exists at: {db_path}")
            else:
                print(f"Database file does not exist at: {db_path}")
            
            # Try a simple query
            user_count = User.query.count()
            print(f"User count: {user_count}")
            
            # Check tables using inspector
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"Database tables: {tables}")
            
            # Check for any clients
            client_count = Client.query.count()
            print(f"Client count: {client_count}")
            
            # Check for any transactions
            transaction_count = Transaction.query.count()
            print(f"Transaction count: {transaction_count}")
            
            if user_count == 0:
                print("No users found. You may need to create an admin user.")
                
            return True
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return False

if __name__ == "__main__":
    check_db_connection() 