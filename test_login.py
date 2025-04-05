from app import app, db
from models import User
from flask_login import current_user, login_user, logout_user
import sys

def test_login():
    with app.app_context():
        try:
            # Check if the User table exists and has any users
            user_count = User.query.count()
            print(f"Found {user_count} users in the database")
            
            if user_count > 0:
                # Get the first user for testing
                user = User.query.first()
                print(f"Test user found: {user.username}, ID: {user.id}")
                print(f"Password hash: {user.password_hash[:20]}...")
                
                # Test Flask-Login functionality in a test request context
                with app.test_request_context():
                    # Check if Flask-Login is working correctly
                    if current_user.is_authenticated:
                        print("WARNING: current_user is already authenticated in a new test context")
                    else:
                        print("current_user is not authenticated (correct)")
                        
                    # Try logging in the user
                    try:
                        login_user(user)
                        if current_user.is_authenticated:
                            print("Login successful, user is now authenticated")
                            print(f"Authenticated user: {current_user.username}")
                            
                            # Test logout
                            logout_user()
                            if not current_user.is_authenticated:
                                print("Logout successful, user is no longer authenticated")
                            else:
                                print("ERROR: Logout failed, user is still authenticated")
                        else:
                            print("ERROR: Login failed, user is still not authenticated")
                    except Exception as e:
                        print(f"ERROR: Exception during login: {str(e)}")
                        print(f"Type: {type(e)}")
                        import traceback
                        traceback.print_exc()
            else:
                print("No users found in the database. Please create a user first.")
                
            # Test password checking
            if user_count > 0:
                user = User.query.first()
                test_password = "password123"  # This should match what we set in reset_password.py
                if user.check_password(test_password):
                    print(f"Password check successful for test password: {test_password}")
                else:
                    print(f"ERROR: Password check failed for test password: {test_password}")
                    print("Try setting a new password with the reset_password.py script.")
                
        except Exception as e:
            print(f"ERROR: Exception during test: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_login() 