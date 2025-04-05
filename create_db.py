from app import app, db
from models import User, Client, Transaction, CompanySettings

with app.app_context():
    # Create all tables in the database
    db.create_all()
    
    # Check if there are any users already
    if User.query.count() == 0:
        # Create default admin user
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('password')  # CHANGE THIS PASSWORD IN PRODUCTION!
        
        # Create default company settings
        settings = CompanySettings(
            name='My Company',
            email='admin@example.com',
            next_invoice_number=1000
        )
        
        db.session.add(admin)
        db.session.add(settings)
        db.session.commit()
        
        print("Created default admin user and company settings")
    else:
        print("Database already contains users - skipping default creation")
        
    print("Database tables created successfully!")