from app import app, db
from models import User

def reset_password():
    with app.app_context():
        # Find the admin user
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("Admin user not found!")
            return
            
        # Reset password to 'password123'
        admin.set_password('password123')
        db.session.commit()
        
        print(f"Password reset for user '{admin.username}'!")
        print("New login credentials:")
        print(f"Username: {admin.username}")
        print(f"Password: password123")

if __name__ == "__main__":
    reset_password() 