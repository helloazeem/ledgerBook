#!/usr/bin/env python3
"""
Check if the application is correctly set up on cPanel
This script verifies the Python environment, dependencies, and app configuration
"""

import os
import sys
import importlib
import traceback

def check_module(module_name):
    """Check if a module can be imported"""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False

def print_result(test_name, result, message=None):
    """Print test results in a formatted way"""
    if result:
        status = "\033[92m[PASS]\033[0m"
    else:
        status = "\033[91m[FAIL]\033[0m"
    
    print(f"{status} {test_name}")
    if message and not result:
        print(f"      > {message}")

def main():
    print("Checking LedgerBook Application Setup")
    print("=====================================")
    
    # Check Python version
    py_ver = sys.version_info
    py_version_ok = py_ver.major >= 3 and py_ver.minor >= 7
    print_result(
        f"Python version {py_ver.major}.{py_ver.minor}.{py_ver.micro}",
        py_version_ok,
        "Python 3.7 or higher is required"
    )
    
    # Check key dependencies
    dependencies = [
        "flask", "flask_sqlalchemy", "flask_login", "flask_wtf",
        "datetime", "uuid", "csv", "io"
    ]
    
    print("\nChecking dependencies:")
    for dep in dependencies:
        has_dep = check_module(dep)
        print_result(dep, has_dep, f"Could not import {dep}")
    
    # Check if the database file path exists
    print("\nChecking application setup:")
    instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
    instance_exists = os.path.isdir(instance_path)
    print_result("Instance directory exists", instance_exists, f"Path: {instance_path}")
    
    # Check if we can import the app
    app_importable = False
    try:
        from app import app
        app_importable = True
    except Exception as e:
        error_msg = traceback.format_exc()
    
    print_result("Import Flask app", app_importable, error_msg if not app_importable else None)
    
    # Check if static directory exists
    static_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static')
    static_exists = os.path.isdir(static_path)
    print_result("Static directory exists", static_exists, f"Path: {static_path}")
    
    # Check if templates directory exists
    templates_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates')
    templates_exist = os.path.isdir(templates_path)
    print_result("Templates directory exists", templates_exist, f"Path: {templates_path}")
    
    # Check if passenger_wsgi.py exists
    passenger_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'passenger_wsgi.py')
    passenger_exists = os.path.isfile(passenger_path)
    print_result("passenger_wsgi.py exists", passenger_exists, f"Path: {passenger_path}")
    
    print("\nSummary:")
    if all([py_version_ok, instance_exists, app_importable, static_exists, templates_exist, passenger_exists]):
        print("\033[92mApplication setup looks good!\033[0m")
    else:
        print("\033[91mApplication setup has issues that need to be fixed.\033[0m")

if __name__ == "__main__":
    main() 