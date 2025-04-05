from app import app
import sys

def test_routes():
    """Test if all main routes work without errors"""
    with app.test_client() as client:
        try:
            print("Testing index route")
            response = client.get('/')
            print(f"Index route status code: {response.status_code}")
            
            print("Testing login route")
            response = client.get('/login-simple')
            print(f"Login route status code: {response.status_code}")
            
        except Exception as e:
            print(f"Error during testing: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("Starting route tests...")
    with app.app_context():
        test_routes()
    print("Completed route tests.") 