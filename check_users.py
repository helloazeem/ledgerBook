from app import app, db
from models import User

def check_users():
    with app.app_context():
        users = User.query.all()
        if users:
            print(f"Found {len(users)} users:")
            for user in users:
                print(f"- Username: {user.username}, Email: {user.email}")
        else:
            print("No users found. You need to register first.")

if __name__ == "__main__":
    check_users() 