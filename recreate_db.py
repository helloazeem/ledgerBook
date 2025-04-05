from app import app, db
from models import User, Client, Transaction, CompanySettings, Todo
import os
import sqlite3
from datetime import datetime, timedelta

# Path to the database file
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'ledgerbook.sqlite3')

# Check if database file exists and delete it
if os.path.exists(db_path):
    try:
        os.remove(db_path)
        print(f"Deleted existing database: {db_path}")
    except Exception as e:
        print(f"Error deleting database: {e}")
else:
    print(f"Database file not found at: {db_path}")

# Make sure the instance directory exists
os.makedirs(os.path.dirname(db_path), exist_ok=True)

# Create a new database with the tables
with app.app_context():
    db.create_all()
    print("Created all database tables")
    
    # Create admin user
    admin = User(username='admin', email='admin@example.com', is_admin=True)
    admin.set_password('password')  # CHANGE THIS PASSWORD IN PRODUCTION!
    
    # Create default company
    company1 = CompanySettings(
        name="My Company",
        email="admin@example.com",
        phone="123-456-7890",
        address="123 Main St\nSuite 100\nAnytown, USA 12345",
        next_invoice_number=1001
    )
    
    # Create a second company for demo
    company2 = CompanySettings(
        name="Second Business",
        email="second@example.com",
        phone="987-654-3210",
        address="456 Oak Ave\nOther City, USA 67890",
        next_invoice_number=5001
    )
    
    # Add companies to admin user and set active company
    admin.companies.append(company1)
    admin.companies.append(company2)
    admin.active_company = company1
    
    # Add sample to-do items
    todo1 = Todo(
        user=admin,
        title="Follow up on overdue invoices",
        description="Call clients with overdue payments",
        due_date=datetime.now().date(),
        priority="high",
        position=1
    )
    
    todo2 = Todo(
        user=admin,
        title="Send monthly statements",
        description="Generate and email monthly statements to all clients",
        due_date=(datetime.now() + timedelta(days=3)).date(),
        priority="medium",
        position=2
    )
    
    # Add to session and commit
    db.session.add(admin)
    db.session.add(company1)
    db.session.add(company2)
    db.session.add(todo1)
    db.session.add(todo2)
    db.session.commit()
    
    # Create sample clients
    client1 = Client(
        name="ABC Corporation",
        email="contact@abccorp.example",
        phone="555-123-4567",
        address="789 Corporate Pkwy\nBusiness City, USA 54321",
        company=company1
    )
    
    client2 = Client(
        name="Smith Consulting",
        email="john@smithconsulting.example",
        phone="555-987-6543",
        company=company1
    )
    
    client3 = Client(
        name="XYZ Industries",
        email="info@xyz.example",
        phone="555-567-8901",
        company=company2
    )
    
    # Add clients to session and commit
    db.session.add(client1)
    db.session.add(client2)
    db.session.add(client3)
    db.session.commit()
    
    # Create sample transactions
    # For client 1
    txn1 = Transaction(
        client=client1,
        date=datetime.now() - timedelta(days=30),
        description="Initial invoice",
        debit=1000.00,
        balance=1000.00,
        due_date=datetime.now() - timedelta(days=15),
        invoice_number=f"INV-{company1.get_next_invoice_number():06d}",
        status="overdue",
        is_paid=False
    )
    
    txn2 = Transaction(
        client=client1,
        date=datetime.now() - timedelta(days=15),
        description="Partial payment",
        credit=500.00,
        balance=500.00,
        invoice_number=None,
        reference="PMT12345"
    )
    
    # For client 2
    txn3 = Transaction(
        client=client2,
        date=datetime.now() - timedelta(days=7),
        description="Consulting services",
        debit=750.00,
        balance=750.00,
        due_date=datetime.now() + timedelta(days=23),
        invoice_number=f"INV-{company1.get_next_invoice_number():06d}",
        status="pending",
        is_paid=False
    )
    
    # For client 3 (in company 2)
    txn4 = Transaction(
        client=client3,
        date=datetime.now() - timedelta(days=5),
        description="Equipment purchase",
        debit=2500.00,
        balance=2500.00,
        due_date=datetime.now() + timedelta(days=25),
        invoice_number=f"INV-{company2.get_next_invoice_number():06d}",
        status="pending",
        is_paid=False
    )
    
    # Add transactions to session and commit
    db.session.add(txn1)
    db.session.add(txn2)
    db.session.add(txn3)
    db.session.add(txn4)
    db.session.commit()
    
    print("Created admin user, companies, clients, and sample data")
    
    # Verify tables were created
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\nTables created:")
    for table in tables:
        print(f"- {table[0]}")
    
    # Verify transaction table structure
    cursor.execute('PRAGMA table_info("transaction");')
    columns = cursor.fetchall()
    print("\nTransaction table columns:")
    for col in columns:
        print(f"- {col[1]} ({col[2]})")
    
    conn.close()

print("\nDatabase reset complete!") 