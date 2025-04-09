import sys
import os
import importlib.util

# Add the application directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask app from app.py
from app import application as flask_app

# This is for older cPanel configurations that use WSGI
def application(environ, start_response):
    # Call Flask app
    return flask_app(environ, start_response) 