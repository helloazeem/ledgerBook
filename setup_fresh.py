import os
import shutil
import sys

def setup_fresh_copy():
    # Define paths
    current_dir = os.getcwd()
    parent_dir = os.path.dirname(current_dir)
    new_dir = os.path.join(parent_dir, 'ledgerbook-app-fresh')
    
    # Check if new directory already exists
    if os.path.exists(new_dir):
        print(f"The directory {new_dir} already exists.")
        choice = input("Do you want to delete it and continue? (y/n): ")
        if choice.lower() != 'y':
            print("Operation cancelled.")
            return
        try:
            shutil.rmtree(new_dir)
            print(f"Removed existing directory: {new_dir}")
        except Exception as e:
            print(f"Error removing directory: {e}")
            return
    
    # Create new directory
    try:
        os.makedirs(new_dir)
        print(f"Created new directory: {new_dir}")
    except Exception as e:
        print(f"Error creating directory: {e}")
        return
    
    # Copy essential files, exclude database files, __pycache__, etc.
    excluded = [
        'instance', '__pycache__', '.git', '.venv', 'venv', 
        'ledgerbook.sqlite3', 'simple_test.sqlite3'
    ]
    
    for item in os.listdir(current_dir):
        if item in excluded or item.endswith('.pyc'):
            continue
        
        src = os.path.join(current_dir, item)
        dst = os.path.join(new_dir, item)
        
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                print(f"Copied directory: {item}")
            else:
                shutil.copy2(src, dst)
                print(f"Copied file: {item}")
        except Exception as e:
            print(f"Error copying {item}: {e}")
    
    # Create a fresh app.py without flask_wtf
    create_fresh_app_py(new_dir)
    
    print("\nSetup complete!")
    print(f"Your fresh project is at: {new_dir}")
    print("\nNext steps:")
    print("1. Navigate to the new directory: cd " + new_dir)
    print("2. Create a new virtual environment: python -m venv venv")
    print("3. Activate it: venv\\Scripts\\activate (Windows) or source venv/bin/activate (Unix)")
    print("4. Install dependencies: pip install -r requirements.txt")
    print("5. Run the app: python app.py")

def create_fresh_app_py(dir_path):
    app_py_path = os.path.join(dir_path, 'app.py')
    
    with open(app_py_path, 'w') as f:
        f.write("""from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
from datetime import datetime
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

# Import db and models from models.py
from models import db, Client, Transaction, User

# Initialize Flask app
app = Flask(__name__)

# Configuration
instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
os.makedirs(instance_path, exist_ok=True)

# SQLite Configuration
SQLITE_DB_PATH = os.path.join(instance_path, "ledgerbook.sqlite3")
DATABASE_URI = f'sqlite:///{SQLITE_DB_PATH}'

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy with the app
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('login.html')
            
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
            
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    clients = Client.query.all()
    return render_template('dashboard.html', clients=clients)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Initialize Database
@app.before_first_request
def create_tables():
    db.create_all()
    
    # Check if admin user exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@example.com')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Created default admin user")

if __name__ == '__main__':
    print("Starting fresh Flask app...")
    app.run(debug=True)
""")
    
    print(f"Created fresh app.py at {app_py_path}")

if __name__ == "__main__":
    setup_fresh_copy() 