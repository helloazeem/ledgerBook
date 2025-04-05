import sys
import os
import importlib

print("Python executable:", sys.executable)
print("Python version:", sys.version)
print("Python path:")
for p in sys.path:
    print(f"  - {p}")

print("\nTrying to import flask_wtf:")
try:
    import flask_wtf
    print(f"  - Imported successfully from: {flask_wtf.__file__}")
except ImportError as e:
    print(f"  - Import error: {e}")

print("\nTrying to import Flask:")
try:
    from flask import Flask
    print(f"  - Imported successfully from: {Flask.__module__}")
except ImportError as e:
    print(f"  - Import error: {e}")

print("\nCurrent directory:", os.getcwd())
print("Files in current directory:")
for f in os.listdir('.'):
    print(f"  - {f}") 