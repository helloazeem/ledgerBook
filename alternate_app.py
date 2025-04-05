from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
from models import db, User, Client

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

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('dashboard_simple.html')
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('login_simple.html')
            
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
            
    return render_template('login_simple.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Check if there are any users - only allow registration if no users exist
    user_count = User.query.count()
    if user_count > 0:
        flash('Registration is disabled. Please contact the administrator.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not email or not password:
            flash('All fields are required', 'error')
            return render_template('register_simple.html')
            
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register_simple.html', username=username, email=email)
                                  
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register_simple.html', email=email)
            
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('register_simple.html', username=username)
            
        # Create new user (omitting company creation for simplicity)
        new_user = User(username=username, email=email, is_admin=True)
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error during registration: {e}', 'error')
            
    return render_template('register_simple.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/clients')
@login_required
def list_clients():
    # Query all clients from the database
    clients = Client.query.all()
    return render_template('clients_simple.html', clients=clients)

@app.route('/clients/add', methods=['GET', 'POST'])
@login_required
def add_client():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        # Validate inputs
        if not name:
            flash('Client name is required.', 'error')
            return render_template('client_form_simple.html', title='Add Client')
                
        # Check if client with same name already exists
        existing_client = Client.query.filter_by(name=name).first()
        if existing_client:
            flash(f'A client named "{name}" already exists.', 'error')
            return render_template('client_form_simple.html', title='Add Client', form_data=request.form)
        
        try:
            new_client = Client(
                name=name,
                email=email,
                phone=phone,
                address=address
            )
            
            db.session.add(new_client)
            db.session.commit()
            
            flash(f'Client "{name}" added successfully.', 'success')
            return redirect(url_for('list_clients'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding client: {e}', 'error')
            return render_template('client_form_simple.html', title='Add Client', form_data=request.form)
    
    # For GET request
    return render_template('client_form_simple.html', title='Add Client')

@app.route('/clients/edit/<int:client_id>', methods=['GET', 'POST'])
@login_required
def edit_client(client_id):
    client = Client.query.get_or_404(client_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        # Validate inputs
        if not name:
            flash('Client name is required.', 'error')
            return render_template('client_form_simple.html', title='Edit Client', client=client)
        
        # Check if the new name already exists (excluding this client)
        existing_client = Client.query.filter(Client.name == name, Client.id != client.id).first()
        if existing_client:
            flash(f'A client named "{name}" already exists.', 'error')
            return render_template('client_form_simple.html', title='Edit Client', client=client, form_data=request.form)
        
        try:
            client.name = name
            client.email = email
            client.phone = phone
            client.address = address
            
            db.session.commit()
            flash(f'Client "{name}" updated successfully.', 'success')
            return redirect(url_for('list_clients'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating client: {e}', 'error')
            return render_template('client_form_simple.html', title='Edit Client', client=client, form_data=request.form)
    
    # For GET request
    return render_template('client_form_simple.html', title='Edit Client', client=client)

@app.route('/transactions')
@login_required
def all_transactions():
    return render_template('transactions_simple.html')

@app.route('/statements')
@login_required
def generate_statement_form():
    return render_template('statements_simple.html')

if __name__ == '__main__':
    app.run(debug=True, port=5003) 