from flask import Flask, render_template_string
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    # Simple template without any complex variables
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test App</title>
    </head>
    <body>
        <h1>Test App is Working</h1>
        <p>If you can see this, your Flask installation is working properly.</p>
    </body>
    </html>
    """
    return render_template_string(template)

def test_routes():
    """Test if all main routes work without errors"""
    with app.test_client() as client:
        logger.info("Testing index route")
        response = client.get('/')
        logger.info(f"Status code: {response.status_code}")
        
        logger.info("Testing login route")
        response = client.get('/login-simple')
        logger.info(f"Status code: {response.status_code}")
        
        logger.info("Testing login form submission")
        response = client.post('/login-simple', data={
            'username': 'admin',
            'password': 'password123',
            'remember': True
        })
        logger.info(f"Status code: {response.status_code}")
        
        # Continue with more route testing
        
if __name__ == "__main__":
    with app.app_context():
        test_routes() 