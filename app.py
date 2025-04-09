from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, make_response, render_template_string
import os
from datetime import datetime, timedelta
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect, CSRFError
import enum
import uuid
import tempfile
import io
from io import StringIO
import csv

# Try to import WeasyPrint, but completely skip it if not available
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except Exception as e:
    print(f"WeasyPrint not available - PDF generation will be disabled: {e}")
    WEASYPRINT_AVAILABLE = False

# Import db and models from models.py
from models import db, Client, Transaction, User, Todo, TodoPriority, CompanySettings, ClientBank

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

# Initialize CSRF protection
csrf = CSRFProtect(app)

# CSRF error handler
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash("The form you submitted is invalid or has expired. Please try again.", "error")
    return redirect(request.referrer or url_for('index'))

# Context processor to add company info to all templates
@app.context_processor
def inject_company_info():
    context = {}
    if current_user.is_authenticated:
        context['user_companies'] = current_user.companies
        context['active_company'] = current_user.active_company
    return context

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate inputs
        if not username or not email or not password:
            flash('Please fill in all required fields.', 'error')
            return render_template('register.html')
            
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        # Check if username is already taken
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already taken. Please choose another.', 'error')
            return render_template('register.html')
        
        # Check if email is already used
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email address already registered.', 'error')
            return render_template('register.html')
        
        try:
            # Create new user
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            # Create a default company for the new user
            default_company = CompanySettings(
                name=f"{username}'s Company",
                email=email,
                next_invoice_number=1001
            )
            
            db.session.add(default_company)
            db.session.commit()
            
            # Associate the default company with the user
            new_user.companies.append(default_company)
            new_user.active_company = default_company
            db.session.commit()
            
            # Automatically log in the new user
            login_user(new_user)
            flash('Registration successful! Welcome to LedgerBook.', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error during registration: {str(e)}', 'error')
            
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Get active company
    company = current_user.active_company
    
    if not company:
        flash('Please create a company first.', 'warning')
        return redirect(url_for('add_company'))
    
    # Use SQLAlchemy functions to optimize queries with fewer database calls
    today = datetime.now().date()
    
    # Use eager loading with joinedload to reduce N+1 query problem
    # Get clients for this company with transactions preloaded
    clients = Client.query.filter_by(company_id=company.id).all()
    
    # Get todos for the current user - add indexing by priority
    todos = Todo.query.filter_by(user_id=current_user.id).order_by(
        Todo.position, 
        Todo.created_at
    ).all()
    
    # Recent transactions with client data in a single query using join
    recent_transactions = db.session.query(Transaction).join(
        Client
    ).options(
        db.joinedload(Transaction.client)  # Eager load client data
    ).filter(
        Client.company_id == company.id
    ).order_by(
        Transaction.date.desc()
    ).limit(5).all()
    
    # Optimize overdue invoices query with joined loading
    overdue_invoices = db.session.query(Transaction).join(
        Client
    ).options(
        db.joinedload(Transaction.client)  # Eager load client data
    ).filter(
        Client.company_id == company.id,
        Transaction.status == 'overdue',
        Transaction.is_paid == False
    ).order_by(
        Transaction.due_date
    ).all()
    
    # Calculate total balance and overdue amounts more efficiently
    # Use SQL aggregation to calculate totals in a single query
    total_balance_result = db.session.query(
        db.func.sum(Transaction.balance)
    ).join(
        Client
    ).filter(
        Client.company_id == company.id,
        Transaction.id.in_(
            db.session.query(db.func.max(Transaction.id)).group_by(Transaction.client_id)
        )
    ).scalar()
    
    total_balance = total_balance_result or 0
    
    # Calculate overdue amount in a single query
    overdue_amount_result = db.session.query(
        db.func.sum(Transaction.debit)
    ).join(
        Client
    ).filter(
        Client.company_id == company.id,
        Transaction.status == 'overdue',
        Transaction.is_paid == False,
        Transaction.debit.isnot(None)
    ).scalar()
    
    overdue_amount = overdue_amount_result or 0
    
    return render_template('dashboard.html', 
                          clients=clients, 
                          todos=todos, 
                          today=today,
                          recent_transactions=recent_transactions,
                          overdue_invoices=overdue_invoices,
                          total_balance=total_balance,
                          overdue_amount=overdue_amount,
                          company=company)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Client Management Routes
@app.route('/clients')
@login_required
def list_clients():
    # Get active company
    company = current_user.active_company
    
    if not company:
        flash('Please create a company first.', 'warning')
        return redirect(url_for('add_company'))
    
    # Get search query if provided
    search_query = request.args.get('q', '')
    
    # Base query - filter by active company
    query = Client.query.filter_by(company_id=company.id)
    
    # Apply search filter if provided
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            (Client.name.like(search_term)) | 
            (Client.email.like(search_term)) | 
            (Client.phone.like(search_term))
        )
    
    # Execute query and get results
    clients = query.order_by(Client.name).all()
    
    return render_template('clients.html', 
                          clients=clients, 
                          search_query=search_query,
                          title="Clients")

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
            return render_template('client_form.html', title='Add Client')
        
        # Check if client with same name already exists
        existing_client = Client.query.filter_by(name=name).first()
        if existing_client:
            flash(f'A client named "{name}" already exists.', 'error')
            return render_template('client_form.html', title='Add Client', form_data=request.form)
        
        try:
            # Get the active company for the current user
            company_id = current_user.active_company_id
            
            # Create new client
            new_client = Client(
                name=name,
                email=email,
                phone=phone,
                address=address,
                company_id=company_id or 1  # Fallback to first company if none active
            )
            
            db.session.add(new_client)
            db.session.commit()
            
            flash(f'Client "{name}" added successfully.', 'success')
            return redirect(url_for('list_clients'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding client: {e}', 'error')
            return render_template('client_form.html', title='Add Client', form_data=request.form)
    
    # For GET request
    return render_template('client_form.html', title='Add Client')

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
            return render_template('client_form.html', title='Edit Client', client=client)
        
        # Check if the new name already exists (excluding this client)
        existing_client = Client.query.filter(Client.name == name, Client.id != client.id).first()
        if existing_client:
            flash(f'A client named "{name}" already exists.', 'error')
            return render_template('client_form.html', title='Edit Client', client=client, form_data=request.form)
        
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
            return render_template('client_form.html', title='Edit Client', client=client, form_data=request.form)
    
    # For GET request
    return render_template('client_form.html', title='Edit Client', client=client)

@app.route('/clients/delete/<int:client_id>', methods=['POST'])
@login_required
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)
    
    try:
        # The cascade will take care of deleting related transactions
        db.session.delete(client)
        db.session.commit()
        flash(f'Client "{client.name}" and all related transactions have been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting client: {e}', 'error')
    
    return redirect(url_for('list_clients'))

# Bank Account Management Routes
@app.route('/clients/<int:client_id>/banks')
@login_required
def client_banks(client_id):
    client = Client.query.filter_by(id=client_id).first_or_404()
    
    # Check if client belongs to active company
    if client.company_id != current_user.active_company_id:
        flash('Access denied. This client does not belong to your active company.', 'error')
        return redirect(url_for('list_clients'))
    
    bank_accounts = ClientBank.query.filter_by(client_id=client_id).order_by(ClientBank.is_primary.desc(), ClientBank.bank_name).all()
    
    return render_template('client_banks.html', 
                          client=client, 
                          bank_accounts=bank_accounts,
                          title=f"Bank Accounts - {client.name}")

@app.route('/clients/<int:client_id>/banks/add', methods=['GET', 'POST'])
@login_required
def add_bank(client_id):
    client = Client.query.filter_by(id=client_id).first_or_404()
    
    # Check if client belongs to active company
    if client.company_id != current_user.active_company_id:
        flash('Access denied. This client does not belong to your active company.', 'error')
        return redirect(url_for('list_clients'))
    
    if request.method == 'POST':
        bank_name = request.form.get('bank_name', '').strip()
        account_name = request.form.get('account_name', '').strip()
        account_number = request.form.get('account_number', '').strip()
        branch = request.form.get('branch', '').strip()
        location = request.form.get('location', '').strip()
        routing_number = request.form.get('routing_number', '').strip()
        is_primary = 'is_primary' in request.form
        
        # Form validation
        if not bank_name or not account_name or not account_number:
            flash('Bank name, account name, and account number are required.', 'error')
            return render_template('bank_form.html', 
                                  client=client,
                                  form_data=request.form)
        
        try:
            # If this is marked as primary, unset all other primary flags
            if is_primary:
                db.session.execute(
                    db.update(ClientBank)
                    .where(ClientBank.client_id == client_id)
                    .values(is_primary=False)
                )
            
            # Create new bank account
            new_bank = ClientBank(
                client_id=client_id,
                bank_name=bank_name,
                account_name=account_name,
                account_number=account_number,
                branch=branch,
                location=location,
                routing_number=routing_number,
                is_primary=is_primary
            )
            
            db.session.add(new_bank)
            db.session.commit()
            
            flash(f'Bank account added successfully.', 'success')
            return redirect(url_for('client_banks', client_id=client_id))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding bank account: {str(e)}")
            flash('There was an error adding the bank account. Please try again.', 'error')
            
    return render_template('bank_form.html', 
                          client=client,
                          title="Add Bank Account")

@app.route('/clients/<int:client_id>/banks/<int:bank_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_bank(client_id, bank_id):
    client = Client.query.filter_by(id=client_id).first_or_404()
    
    # Check if client belongs to active company
    if client.company_id != current_user.active_company_id:
        flash('Access denied. This client does not belong to your active company.', 'error')
        return redirect(url_for('list_clients'))
    
    # Get bank account and verify ownership
    bank = ClientBank.query.filter_by(id=bank_id, client_id=client_id).first_or_404()
    
    if request.method == 'POST':
        bank_name = request.form.get('bank_name', '').strip()
        account_name = request.form.get('account_name', '').strip()
        account_number = request.form.get('account_number', '').strip()
        branch = request.form.get('branch', '').strip()
        location = request.form.get('location', '').strip()
        routing_number = request.form.get('routing_number', '').strip()
        is_primary = 'is_primary' in request.form
        
        # Form validation
        if not bank_name or not account_name or not account_number:
            flash('Bank name, account name, and account number are required.', 'error')
            return render_template('bank_form.html', 
                                  client=client,
                                  bank=bank)
        
        try:
            # If this is marked as primary, unset all other primary flags
            if is_primary and not bank.is_primary:
                db.session.execute(
                    db.update(ClientBank)
                    .where(ClientBank.client_id == client_id)
                    .values(is_primary=False)
                )
            
            # Update bank account
            bank.bank_name = bank_name
            bank.account_name = account_name
            bank.account_number = account_number
            bank.branch = branch
            bank.location = location
            bank.routing_number = routing_number
            bank.is_primary = is_primary
            
            db.session.commit()
            
            flash(f'Bank account updated successfully.', 'success')
            return redirect(url_for('client_banks', client_id=client_id))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating bank account: {str(e)}")
            flash('There was an error updating the bank account. Please try again.', 'error')
            
    return render_template('bank_form.html', 
                          client=client,
                          bank=bank,
                          title="Edit Bank Account")

@app.route('/clients/<int:client_id>/banks/<int:bank_id>/delete', methods=['POST'])
@login_required
def delete_bank(client_id, bank_id):
    client = Client.query.filter_by(id=client_id).first_or_404()
    
    # Check if client belongs to active company
    if client.company_id != current_user.active_company_id:
        flash('Access denied. This client does not belong to your active company.', 'error')
        return redirect(url_for('list_clients'))
    
    # Get bank account and verify ownership
    bank = ClientBank.query.filter_by(id=bank_id, client_id=client_id).first_or_404()
    
    try:
        was_primary = bank.is_primary
        
        # Delete bank account
        db.session.delete(bank)
        
        # If this was the primary account, set another one as primary if available
        if was_primary:
            next_bank = ClientBank.query.filter_by(client_id=client_id).first()
            if next_bank:
                next_bank.is_primary = True
        
        db.session.commit()
        flash('Bank account deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting bank account: {str(e)}")
        flash(f'Error deleting bank account: {e}', 'error')
        
    return redirect(url_for('client_banks', client_id=client_id))

@app.route('/api/banks/<int:bank_id>')
@login_required
def api_get_bank(bank_id):
    # Get bank details for AJAX requests (used in popup modal)
    bank = ClientBank.query.filter_by(id=bank_id).first_or_404()
    
    # Check if bank belongs to a client in the active company
    client = Client.query.filter_by(id=bank.client_id).first_or_404()
    if client.company_id != current_user.active_company_id:
        return jsonify({"error": "Access denied"}), 403
    
    return jsonify({
        "id": bank.id,
        "bank_name": bank.bank_name,
        "account_name": bank.account_name,
        "account_number": bank.account_number,
        "branch": bank.branch or "",
        "location": bank.location or "",
        "routing_number": bank.routing_number or "",
        "is_primary": bank.is_primary
    })

# Transaction Management Routes
@app.route('/transactions')
@login_required
def all_transactions():
    # Get query parameters
    search_query = request.args.get('q', '')
    client_id = request.args.get('client_id', '')
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Get active company
    company = current_user.active_company
    
    if not company:
        flash('Please create a company first.', 'warning')
        return redirect(url_for('add_company'))
    
    # Base query - join with Client to filter by company
    query = Transaction.query.join(Client).filter(Client.company_id == company.id)
    
    # Apply filters
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            (Transaction.description.like(search_term)) | 
            (Transaction.invoice_number.like(search_term)) | 
            (Transaction.reference.like(search_term))
        )
        
    if client_id:
        query = query.filter(Transaction.client_id == client_id)
        
    if status_filter:
        query = query.filter(Transaction.status == status_filter)
        
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Transaction.date) >= date_from_obj)
        except ValueError:
            flash('Invalid "From" date format. Please use YYYY-MM-DD.', 'error')
            
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Transaction.date) <= date_to_obj)
        except ValueError:
            flash('Invalid "To" date format. Please use YYYY-MM-DD.', 'error')
    
    # Execute query and get results
    transactions = query.order_by(Transaction.date.desc()).all()
    
    # Get all clients for the filter dropdown, filtered by active company
    clients = Client.query.filter_by(company_id=company.id).all()
    
    return render_template('transactions.html', 
                          transactions=transactions,
                          clients=clients,
                          search_query=search_query,
                          client_id=client_id,
                          status_filter=status_filter,
                          date_from=date_from,
                          date_to=date_to)

@app.route('/client/<int:client_id>/transactions')
@login_required
def view_client_transactions(client_id):
    client = Client.query.get_or_404(client_id)
    
    # Get transactions for this client
    transactions = client.transactions.order_by(Transaction.date.desc()).all()
    
    return render_template('client_transactions.html', 
                          client=client, 
                          transactions=transactions)

@app.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    # Get client_id from query parameter if it exists
    client_id = request.args.get('client_id', type=int)
    client = None
    
    if client_id:
        client = Client.query.get_or_404(client_id)
    
    # Get all clients for the dropdown
    clients = Client.query.order_by(Client.name).all()
    
    if request.method == 'POST':
        # Get form data
        client_id = client_id or request.form.get('client_id', type=int)
        date_str = request.form.get('date')
        due_date_str = request.form.get('due_date')
        description = request.form.get('description')
        amount_type = request.form.get('amount_type')
        amount = request.form.get('amount', type=float)
        reference = request.form.get('reference')
        is_paid = 'is_paid' in request.form
        
        # Validation
        if not client_id:
            flash('Please select a client.', 'error')
            return render_template('transaction_form.html', clients=clients, form_data=request.form)
        
        if not description:
            flash('Description is required.', 'error')
            return render_template('transaction_form.html', client=client, clients=clients, form_data=request.form)
        
        if not date_str:
            flash('Date is required.', 'error')
            return render_template('transaction_form.html', client=client, clients=clients, form_data=request.form)
        
        if not amount or amount <= 0:
            flash('Amount must be greater than zero.', 'error')
            return render_template('transaction_form.html', client=client, clients=clients, form_data=request.form)
        
        try:
            # Get client
            client = Client.query.get(client_id)
            if not client:
                flash('Invalid client selected.', 'error')
                return render_template('transaction_form.html', clients=clients, form_data=request.form)
            
            # Parse dates
            transaction_date = datetime.strptime(date_str, '%Y-%m-%d')
            due_date = None
            if due_date_str:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            
            # Determine if this is a debit or credit
            debit = amount if amount_type == 'debit' else None
            credit = amount if amount_type == 'credit' else None
            
            # Get the latest balance for this client
            latest_transaction = client.transactions.order_by(Transaction.date.desc(), Transaction.id.desc()).first()
            current_balance = latest_transaction.balance if latest_transaction else 0
            
            # Calculate new balance
            if debit:
                new_balance = current_balance + debit
            else:
                new_balance = current_balance - credit
            
            # Get active company to generate invoice number
            company = current_user.active_company
            invoice_number = None
            
            # Only generate invoice number for debit transactions
            if debit and company:
                invoice_number = f"INV-{company.get_next_invoice_number()}"
            
            # Create and save transaction
            transaction = Transaction(
                client_id=client_id,
                date=transaction_date,
                due_date=due_date,
                description=description,
                debit=debit,
                credit=credit,
                balance=new_balance,
                reference=reference,
                invoice_number=invoice_number,
                is_paid=is_paid
            )
            
            # Update transaction status
            transaction.update_status()
            
            db.session.add(transaction)
            db.session.commit()
            
            flash('Transaction added successfully.', 'success')
            
            # Redirect based on context
            if client:
                return redirect(url_for('view_client_transactions', client_id=client.id))
            else:
                return redirect(url_for('all_transactions'))
            
        except ValueError as e:
            flash(f'Invalid date format: {e}', 'error')
            return render_template('transaction_form.html', client=client, clients=clients, form_data=request.form)
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding transaction: {e}', 'error')
            return render_template('transaction_form.html', client=client, clients=clients, form_data=request.form)
    
    # For GET request
    return render_template('transaction_form.html', client=client, clients=clients)

@app.route('/transactions/<int:transaction_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    client = Client.query.get(transaction.client_id)
    
    if request.method == 'POST':
        description = request.form.get('description')
        date_str = request.form.get('date')
        due_date_str = request.form.get('due_date')
        reference = request.form.get('reference')
        is_paid = 'is_paid' in request.form
        
        # Validation
        if not description:
            flash('Description is required.', 'error')
            return render_template('transaction_form.html', transaction=transaction, client=client)
        
        if not date_str:
            flash('Date is required.', 'error')
            return render_template('transaction_form.html', transaction=transaction, client=client)
        
        try:
            # Update basic fields
            transaction.description = description
            transaction.date = datetime.strptime(date_str, '%Y-%m-%d')
            transaction.reference = reference
            transaction.is_paid = is_paid
            
            if due_date_str:
                transaction.due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            else:
                transaction.due_date = None
            
            # Update status
            transaction.update_status()
            
            db.session.commit()
            flash('Transaction updated successfully.', 'success')
            
            # Redirect based on context
            if 'client_transactions' in request.referrer:
                return redirect(url_for('view_client_transactions', client_id=client.id))
            else:
                return redirect(url_for('all_transactions'))
            
        except ValueError as e:
            flash(f'Invalid date format: {e}', 'error')
            return render_template('transaction_form.html', transaction=transaction, client=client)
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating transaction: {e}', 'error')
            return render_template('transaction_form.html', transaction=transaction, client=client)
    
    # For GET request
    return render_template('transaction_form.html', transaction=transaction, client=client)

@app.route('/transactions/<int:transaction_id>/delete', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    client_id = transaction.client_id
    
    try:
        db.session.delete(transaction)
        db.session.commit()
        
        # Update balances for all subsequent transactions
        client = Client.query.get(client_id)
        transactions = client.transactions.order_by(Transaction.date, Transaction.id).all()
        
        running_balance = 0
        for idx, tx in enumerate(transactions):
            if tx.debit:
                running_balance += tx.debit
            if tx.credit:
                running_balance -= tx.credit
            
            tx.balance = running_balance
            
        db.session.commit()
        
        flash('Transaction deleted successfully and balances recalculated.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting transaction: {e}', 'error')
    
    # Check if we should return to client transactions view
    if 'client_transactions' in request.referrer:
        return redirect(url_for('view_client_transactions', client_id=client_id))
    else:
        return redirect(url_for('all_transactions'))

# Statement Management Routes
@app.route('/statements')
@login_required
def list_statements():
    # Get all clients for statement generation
    clients = Client.query.order_by(Client.name).all()
    return render_template('statements_simple.html', clients=clients)

@app.route('/statements/generate', methods=['GET', 'POST'])
@login_required
def generate_statement_form():
    # Get client_id from query parameter if it exists
    client_id = request.args.get('client_id', type=int)
    clients = Client.query.order_by(Client.name).all()
    
    if request.method == 'POST':
        client_id = request.form.get('client_id', type=int)
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        include_unpaid_only = 'include_unpaid_only' in request.form
        
        if not client_id:
            flash('Please select a client.', 'error')
            return render_template('statement_form.html', clients=clients)
        
        if not start_date_str or not end_date_str:
            flash('Start and end dates are required.', 'error')
            return render_template('statement_form.html', clients=clients, client_id=client_id)
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            if start_date > end_date:
                flash('Start date must be before end date.', 'error')
                return render_template('statement_form.html', clients=clients, client_id=client_id)
            
            # Redirect to statement view
            return redirect(url_for('view_statement', 
                                   client_id=client_id, 
                                   start_date=start_date_str, 
                                   end_date=end_date_str,
                                   unpaid_only='1' if include_unpaid_only else '0'))
            
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
            return render_template('statement_form.html', clients=clients, client_id=client_id)
    
    # For GET request
    return render_template('statement_form.html', clients=clients, client_id=client_id)

@app.route('/statements/view', methods=['GET', 'POST'])
@login_required
def view_statement():
    client_id = request.args.get('client_id', type=int) if request.method == 'GET' else request.form.get('client_id', type=int)
    start_date_str = request.args.get('start_date') if request.method == 'GET' else request.form.get('start_date')
    end_date_str = request.args.get('end_date') if request.method == 'GET' else request.form.get('end_date')
    unpaid_only = request.args.get('unpaid_only') == '1' if request.method == 'GET' else 'unpaid_only' in request.form
    
    if not client_id or not start_date_str or not end_date_str:
        flash('Missing required parameters.', 'error')
        return redirect(url_for('generate_statement_form'))
    
    try:
        client = Client.query.get_or_404(client_id)
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        end_date = datetime.combine(end_date.date(), datetime.max.time())  # End of day
        
        # Get opening balance (sum of all transactions before start date)
        opening_balance_query = db.session.query(db.func.coalesce(db.func.sum(Transaction.debit), 0) - 
                                              db.func.coalesce(db.func.sum(Transaction.credit), 0))\
                             .filter(Transaction.client_id == client_id,
                                    db.func.date(Transaction.date) < start_date.date())
        
        opening_balance = opening_balance_query.scalar() or 0
        
        # Build query for statement transactions
        query = Transaction.query.filter(
            Transaction.client_id == client_id,
            db.func.date(Transaction.date) >= start_date.date(),
            db.func.date(Transaction.date) <= end_date.date()
        )
        
        if unpaid_only:
            query = query.filter(Transaction.is_paid == False)
        
        # Get transactions and sort by date
        transactions = query.order_by(Transaction.date, Transaction.id).all()
        
        # Calculate running balance
        running_balance = opening_balance
        statement_transactions = []
        
        for tx in transactions:
            if tx.debit:
                running_balance += tx.debit
            if tx.credit:
                running_balance -= tx.credit
                
            # Create a dict with transaction data and running balance
            tx_dict = {
                'id': tx.id,
                'date': tx.date,
                'due_date': tx.due_date,
                'description': tx.description,
                'invoice_number': tx.invoice_number,
                'reference': tx.reference,
                'debit': tx.debit,
                'credit': tx.credit,
                'balance': running_balance,
                'is_paid': tx.is_paid,
                'status': tx.status
            }
            statement_transactions.append(tx_dict)
        
        # Get company information
        company = current_user.active_company or CompanySettings.get_settings()
        
        # Calculate statement totals
        total_debit = sum(tx.debit or 0 for tx in transactions)
        total_credit = sum(tx.credit or 0 for tx in transactions)
        closing_balance = opening_balance + total_debit - total_credit
        
        return render_template('statement_view.html',
                              client=client,
                              company=company,
                              start_date=start_date,
                              end_date=end_date,
                              opening_balance=opening_balance,
                              transactions=statement_transactions,
                              total_debit=total_debit,
                              total_credit=total_credit,
                              closing_balance=closing_balance,
                              unpaid_only=unpaid_only)
                              
    except ValueError:
        flash('Invalid date format.', 'error')
        return redirect(url_for('generate_statement_form'))
    except Exception as e:
        flash(f'Error generating statement: {e}', 'error')
        return redirect(url_for('generate_statement_form'))

# Todo Routes
@app.route('/todos/add', methods=['GET', 'POST'])
@login_required
def add_todo():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date', '').strip()
        priority = request.form.get('priority', TodoPriority.MEDIUM.value)
        is_completed = 'is_completed' in request.form
        
        # Form validation
        if not title:
            flash('Task title is required.', 'error')
            return render_template('todo_form.html', 
                                  form_data={'description': description, 'due_date': due_date_str, 'priority': priority})
        
        # Validate priority
        if priority not in [p.value for p in TodoPriority]:
            priority = TodoPriority.MEDIUM.value
        
        todo = Todo(
            user_id=current_user.id,
            title=title,
            description=description,
            is_completed=is_completed,
            priority=priority
        )
        
        # Handle due date parsing
        if due_date_str:
            try:
                todo.due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
                return render_template('todo_form.html', 
                                      form_data={'title': title, 'description': description, 'priority': priority})
        
        # Get the highest position number and add 1
        max_position = db.session.query(db.func.max(Todo.position)).filter(
            Todo.user_id == current_user.id
        ).scalar() or 0
        todo.position = max_position + 1
        
        try:
            db.session.add(todo)
            db.session.commit()
            flash('Task added successfully.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding todo: {str(e)}")
            flash('There was an error adding your task. Please try again.', 'error')
            
    return render_template('todo_form.html')

@app.route('/todos/<int:todo_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_todo(todo_id):
    # Use a single database query with first_or_404 to handle the case when todo doesn't exist
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date', '').strip()
        priority = request.form.get('priority', todo.priority)
        is_completed = 'is_completed' in request.form
        
        # Form validation
        if not title:
            flash('Task title is required.', 'error')
            return render_template('todo_form.html', todo=todo)
        
        # Validate priority
        if priority not in [p.value for p in TodoPriority]:
            priority = todo.priority
        
        try:
            todo.title = title
            todo.description = description
            todo.is_completed = is_completed
            todo.priority = priority
            
            # Handle due date parsing
            if due_date_str:
                try:
                    todo.due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
                    return render_template('todo_form.html', todo=todo)
            else:
                todo.due_date = None
            
            db.session.commit()
            flash('Task updated successfully.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating todo: {str(e)}")
            flash('There was an error updating your task. Please try again.', 'error')
            
    return render_template('todo_form.html', todo=todo)

@app.route('/todos/<int:todo_id>/toggle', methods=['POST'])
@login_required
def toggle_todo(todo_id):
    # Check if request has proper JSON content type
    if not request.is_json:
        return jsonify({"success": False, "message": "Invalid request format, expected JSON"}), 400
    
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"success": False, "message": "Missing request data"}), 400
            
        is_completed = data.get('is_completed')
        if is_completed is None:
            return jsonify({"success": False, "message": "Missing is_completed parameter"}), 400
            
        # Use a single database query to find and verify the todo
        todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()
        
        if not todo:
            return jsonify({"success": False, "message": "Task not found or access denied"}), 404
        
        todo.is_completed = is_completed
        db.session.commit()
        
        return jsonify({"success": True, "data": {"id": todo.id, "is_completed": todo.is_completed}})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error toggling todo {todo_id}: {str(e)}")
        return jsonify({"success": False, "message": "An error occurred while updating the task"}), 500

@app.route('/todos/<int:todo_id>/position', methods=['POST'])
@login_required
def update_todo_position(todo_id):
    # Check if request has proper JSON content type
    if not request.is_json:
        return jsonify({"success": False, "message": "Invalid request format, expected JSON"}), 400
        
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"success": False, "message": "Missing request data"}), 400
            
        new_position = data.get('position')
        todo_order = data.get('order', [])
        
        if new_position is None or not todo_order:
            return jsonify({"success": False, "message": "Position and order data are required"}), 400
        
        # First verify the todo exists and belongs to the current user
        todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()
        if not todo:
            return jsonify({"success": False, "message": "Task not found or access denied"}), 404
        
        # Verify all todos in the order belong to the current user
        # Convert all IDs to integers and filter out any that don't belong to the user
        todo_ids = [int(id_str) for id_str in todo_order if id_str.isdigit()]
        valid_todos = Todo.query.filter(Todo.id.in_(todo_ids), Todo.user_id == current_user.id).all()
        valid_todo_ids = {t.id for t in valid_todos}
        
        # Update positions in a single transaction
        for i, id_str in enumerate(todo_order):
            if not id_str.isdigit():
                continue
                
            curr_todo_id = int(id_str)
            if curr_todo_id not in valid_todo_ids:
                continue
                
            # Bulk update is more efficient than individual updates
            db.session.execute(
                db.update(Todo)
                .where(Todo.id == curr_todo_id)
                .values(position=i)
            )
        
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating todo position: {str(e)}")
        return jsonify({"success": False, "message": "An error occurred while updating the task order"}), 500

@app.route('/todos/<int:todo_id>/delete', methods=['POST'])
@login_required
def delete_todo(todo_id):
    try:
        # Use a single query to find and check ownership
        todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()
        
        if not todo:
            return jsonify({'success': False, 'message': 'Task not found or access denied'}), 404
        
        # Get the position of the todo to be deleted
        deleted_position = todo.position
        
        # Delete the todo
        db.session.delete(todo)
        
        # Update positions of remaining todos to maintain sequential ordering
        db.session.flush()  # Ensure the deletion is processed before the update
        
        # Shift all tasks with higher positions down by 1
        db.session.execute(
            db.update(Todo)
            .where(Todo.user_id == current_user.id, Todo.position > deleted_position)
            .values(position=Todo.position - 1)
        )
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting todo {todo_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while deleting the task'}), 500

# Company Management Routes
@app.route('/company/settings', methods=['GET', 'POST'])
@login_required
def company_settings():
    # Get active company or default
    company = current_user.active_company
    
    if not company:
        flash('Please create a company first.', 'warning')
        return redirect(url_for('add_company'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        # Validate inputs
        if not name:
            flash('Company name is required.', 'error')
            return render_template('settings.html', company=company)
        
        try:
            company.name = name
            company.email = email
            company.phone = phone
            company.address = address
            
            db.session.commit()
            flash(f'Company settings updated successfully.', 'success')
            return redirect(url_for('company_settings'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating company settings: {e}', 'error')
    
    return render_template('settings.html', company=company)

@app.route('/company/add', methods=['GET', 'POST'])
@login_required
def add_company():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        # Validate inputs
        if not name:
            flash('Company name is required.', 'error')
            return render_template('company_form.html')
        
        # Check if company with same name already exists
        existing_company = CompanySettings.query.filter_by(name=name).first()
        if existing_company:
            flash(f'A company named "{name}" already exists.', 'error')
            return render_template('company_form.html', form_data=request.form)
        
        try:
            new_company = CompanySettings(
                name=name,
                email=email,
                phone=phone,
                address=address,
                next_invoice_number=1001
            )
            
            db.session.add(new_company)
            db.session.commit()
            
            # Associate company with current user
            current_user.companies.append(new_company)
            
            # Set as active company if user doesn't have one yet
            if not current_user.active_company:
                current_user.active_company = new_company
                
            db.session.commit()
            
            flash(f'Company "{name}" added successfully.', 'success')
            return redirect(url_for('company_settings'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding company: {e}', 'error')
            return render_template('company_form.html', form_data=request.form)
    
    # For GET request
    return render_template('company_form.html')

@app.route('/company/edit/<int:company_id>', methods=['GET', 'POST'])
@login_required
def edit_company(company_id):
    company = CompanySettings.query.get_or_404(company_id)
    
    # Check if user has access to this company
    if current_user.is_admin or company in current_user.companies:
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            address = request.form.get('address')
            next_invoice_number = request.form.get('next_invoice_number', type=int)
            
            # Validate inputs
            if not name:
                flash('Company name is required.', 'error')
                return render_template('company_form.html', company=company)
            
            if not next_invoice_number or next_invoice_number < 1:
                flash('Next invoice number must be a positive integer.', 'error')
                return render_template('company_form.html', company=company, form_data=request.form)
            
            try:
                company.name = name
                company.email = email
                company.phone = phone
                company.address = address
                company.next_invoice_number = next_invoice_number
                
                db.session.commit()
                flash(f'Company "{name}" updated successfully.', 'success')
                return redirect(url_for('company_settings'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating company: {e}', 'error')
                return render_template('company_form.html', company=company, form_data=request.form)
        
        # For GET request
        return render_template('company_form.html', company=company)
    else:
        flash('You do not have permission to edit this company.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/switch-company/<int:company_id>')
@login_required
def switch_company(company_id):
    company = CompanySettings.query.get_or_404(company_id)
    
    # Check if user has access to this company
    if company in current_user.companies:
        current_user.active_company = company
        db.session.commit()
        flash(f'Switched to {company.name}.', 'success')
    else:
        flash('You do not have access to this company.', 'error')
    
    # Redirect back to the previous page or dashboard
    next_page = request.referrer or url_for('dashboard')
    return redirect(next_page)

# Financial Reports
@app.route('/reports')
@login_required
def reports():
    # Get active company
    company = current_user.active_company
    
    if not company:
        flash('Please create a company first.', 'warning')
        return redirect(url_for('add_company'))
    
    # Get query parameters
    today = datetime.now().date()
    date_from = request.args.get('date_from', (today - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.args.get('date_to', today.strftime('%Y-%m-%d'))
    group_by = request.args.get('group_by', 'day')
    
    try:
        start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        end_date_time = datetime.combine(end_date, datetime.max.time())
    except ValueError:
        flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
        start_date = today - timedelta(days=30)
        end_date = today
        end_date_time = datetime.combine(end_date, datetime.max.time())
    
    # Get all transactions for this company within date range
    transactions = Transaction.query.join(Client).filter(
        Client.company_id == company.id,
        db.func.date(Transaction.date) >= start_date,
        db.func.date(Transaction.date) <= end_date
    ).order_by(Transaction.date).all()
    
    # Calculate totals
    total_income = sum(tx.credit or 0 for tx in transactions)
    total_expenses = sum(tx.debit or 0 for tx in transactions)
    net_profit = total_income - total_expenses
    
    # Generate data for charts based on group_by selection
    labels = []
    income_data = []
    expense_data = []
    
    if group_by == 'day':
        current_date = start_date
        while current_date <= end_date:
            labels.append(current_date.strftime('%Y-%m-%d'))
            
            # Calculate daily amounts
            daily_income = sum(tx.credit or 0 for tx in transactions 
                              if tx.date.date() == current_date)
            daily_expense = sum(tx.debit or 0 for tx in transactions 
                               if tx.date.date() == current_date)
            
            income_data.append(daily_income)
            expense_data.append(daily_expense)
            
            current_date += timedelta(days=1)
            
    elif group_by == 'week':
        # Group by week
        current_date = start_date
        while current_date <= end_date:
            # Start of week (Monday)
            week_start = current_date - timedelta(days=current_date.weekday())
            # End of week (Sunday)
            week_end = week_start + timedelta(days=6)
            
            if week_end > end_date:
                week_end = end_date
                
            labels.append(f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}")
            
            # Calculate weekly amounts
            weekly_income = sum(tx.credit or 0 for tx in transactions 
                               if week_start <= tx.date.date() <= week_end)
            weekly_expense = sum(tx.debit or 0 for tx in transactions 
                                if week_start <= tx.date.date() <= week_end)
            
            income_data.append(weekly_income)
            expense_data.append(weekly_expense)
            
            current_date = week_end + timedelta(days=1)
            
    elif group_by == 'month':
        # Group by month
        current_month = start_date.replace(day=1)
        while current_month <= end_date:
            next_month = current_month.replace(day=28) + timedelta(days=4)
            month_end = next_month.replace(day=1) - timedelta(days=1)
            
            if month_end > end_date:
                month_end = end_date
                
            labels.append(current_month.strftime('%b %Y'))
            
            # Calculate monthly amounts
            monthly_income = sum(tx.credit or 0 for tx in transactions 
                                if current_month <= tx.date.date() <= month_end)
            monthly_expense = sum(tx.debit or 0 for tx in transactions 
                                 if current_month <= tx.date.date() <= month_end)
            
            income_data.append(monthly_income)
            expense_data.append(monthly_expense)
            
            # Move to next month
            current_month = (current_month.replace(day=28) + timedelta(days=4)).replace(day=1)
    
    # Get top clients by revenue
    client_revenue = {}
    
    for tx in transactions:
        if tx.credit:  # Only count credits (payments) as revenue
            client_id = tx.client_id
            if client_id not in client_revenue:
                client_revenue[client_id] = 0
            client_revenue[client_id] += tx.credit
    
    # Get client details and calculate percentages
    top_clients = []
    
    if client_revenue:
        for client_id, revenue in sorted(client_revenue.items(), key=lambda x: x[1], reverse=True)[:5]:
            client = Client.query.get(client_id)
            if client:
                percentage = (revenue / total_income * 100) if total_income > 0 else 0
                top_clients.append({
                    'id': client.id,
                    'name': client.name,
                    'revenue': revenue,
                    'percentage': percentage
                })
    
    return render_template('reports.html',
                          date_from=date_from,
                          date_to=date_to,
                          group_by=group_by,
                          total_income=total_income,
                          total_expenses=total_expenses,
                          net_profit=net_profit,
                          labels=labels,
                          income_data=income_data,
                          expense_data=expense_data,
                          top_clients=top_clients)

# Invoice generation
@app.route('/invoices/generate/<int:client_id>', methods=['GET', 'POST'])
@login_required
def generate_invoice(client_id):
    client = Client.query.get_or_404(client_id)
    
    # Make sure client belongs to active company
    if client.company_id != current_user.active_company_id:
        flash('Access denied: Client does not belong to your active company.', 'error')
        return redirect(url_for('list_clients'))
    
    if request.method == 'POST':
        # Get form data
        invoice_number = request.form.get('invoice_number') or f"INV-{uuid.uuid4().hex[:8].upper()}"
        invoice_date = datetime.strptime(request.form.get('invoice_date'), '%Y-%m-%d')
        due_date_str = request.form.get('due_date')
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d') if due_date_str else None
        
        # Get selected transactions
        selected_transaction_ids = request.form.getlist('transaction_ids')
        if not selected_transaction_ids:
            flash('Please select at least one transaction to include in the invoice.', 'error')
            return redirect(url_for('generate_invoice', client_id=client_id))
        
        # Get the transactions
        transactions = Transaction.query.filter(
            Transaction.id.in_(selected_transaction_ids),
            Transaction.client_id == client_id,
            Transaction.debit > 0,  # Only include debits (charges)
            Transaction.is_paid == False  # Only include unpaid items
        ).all()
        
        if not transactions:
            flash('No valid transactions selected for invoicing.', 'error')
            return redirect(url_for('generate_invoice', client_id=client_id))
        
        # Calculate invoice totals
        subtotal = sum(tx.debit for tx in transactions)
        tax_rate = float(request.form.get('tax_rate') or 0)
        tax_amount = subtotal * (tax_rate / 100)
        total = subtotal + tax_amount
        
        # Prepare data for invoice template
        invoice = {
            'number': invoice_number,
            'date': invoice_date,
            'due_date': due_date,
            'subtotal': subtotal,
            'tax_rate': tax_rate,
            'tax_amount': tax_amount,
            'total': total,
            'status': 'unpaid'
        }
        
        # Convert transactions to invoice items
        invoice_items = [{
            'description': tx.description,
            'date': tx.date,
            'amount': tx.debit
        } for tx in transactions]
        
        # Get company info
        company = current_user.active_company or CompanySettings.get_settings()
        
        # Generate invoice HTML
        invoice_html = render_template('invoice.html',
                                     invoice=invoice,
                                     invoice_items=invoice_items,
                                     client=client,
                                     company=company)
        
        # Determine if we should display, download or mark transactions as invoiced
        action = request.form.get('action', 'preview')
        
        if action == 'download':
            if WEASYPRINT_AVAILABLE:
                # Generate PDF using WeasyPrint
                pdf = HTML(string=invoice_html).write_pdf()
                
                # Return PDF as download
                response = make_response(pdf)
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Content-Disposition'] = f'attachment; filename=Invoice-{invoice_number}.pdf'
                
                return response
            else:
                # Alternative approach: Just show the HTML with a print message
                flash("PDF generation is not available. Please use your browser's print function to save as PDF.", "warning")
                return render_template('invoice_preview.html',
                                    invoice_html=invoice_html,
                                    invoice=invoice,
                                    client=client,
                                    transactions=transactions,
                                    pdf_disabled=True)
        
        elif action == 'save':
            # Mark transactions as invoiced
            for tx in transactions:
                tx.invoice_number = invoice_number
                if due_date:
                    tx.due_date = due_date
            
            db.session.commit()
            flash(f'Invoice {invoice_number} has been generated and transactions have been updated.', 'success')
            return redirect(url_for('view_client_transactions', client_id=client_id))
        
        # Default: preview
        return render_template('invoice_preview.html',
                              invoice_html=invoice_html,
                              invoice=invoice,
                              client=client,
                              transactions=transactions)
    
    # For GET request: Display form with unpaid transactions
    unpaid_transactions = Transaction.query.filter(
        Transaction.client_id == client_id,
        Transaction.debit > 0,  # Only include debits (charges)
        Transaction.is_paid == False  # Only include unpaid items
    ).order_by(Transaction.date).all()
    
    # Generate a default invoice number
    default_invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
    
    # Get default dates
    today = datetime.now().date()
    default_due_date = (today + timedelta(days=30)).strftime('%Y-%m-%d')
    
    return render_template('invoice_form.html',
                          client=client,
                          transactions=unpaid_transactions,
                          invoice_number=default_invoice_number,
                          invoice_date=today.strftime('%Y-%m-%d'),
                          due_date=default_due_date)

# Initialize Database
# Replace the deprecated @app.before_first_request
_is_db_initialized = False

@app.before_request
def initialize_db():
    global _is_db_initialized
    if not _is_db_initialized:
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', email='admin@example.com')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Created default admin user")
        
        _is_db_initialized = True

# Add this function after all the Todo routes
@app.route('/todos/export', methods=['GET'])
@login_required
def export_todos():
    try:
        # Get filter parameter
        filter_type = request.args.get('filter', 'all')
        
        # Base query
        query = Todo.query.filter_by(user_id=current_user.id)
        
        # Apply filters
        if filter_type == 'active':
            query = query.filter_by(is_completed=False)
        elif filter_type == 'completed':
            query = query.filter_by(is_completed=True)
        elif filter_type == 'overdue':
            query = query.filter(
                Todo.is_completed == False,
                Todo.due_date.isnot(None),
                Todo.due_date < datetime.now()
            )
            
        # Get todos ordered by position
        todos = query.order_by(Todo.position, Todo.created_at).all()
        
        # Create a CSV string
        csv_data = StringIO()
        csv_writer = csv.writer(csv_data)
        
        # Write header
        csv_writer.writerow(['Title', 'Description', 'Due Date', 'Priority', 'Status', 'Created At'])
        
        # Write data
        for todo in todos:
            csv_writer.writerow([
                todo.title,
                todo.description or '',
                todo.due_date.strftime('%Y-%m-%d') if todo.due_date else '',
                todo.priority,
                'Completed' if todo.is_completed else 'Active',
                todo.created_at.strftime('%Y-%m-%d %H:%M')
            ])
            
        # Create response
        response = make_response(csv_data.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=todos_{filter_type}_{datetime.now().strftime("%Y%m%d")}.csv'
        
        return response
        
    except Exception as e:
        app.logger.error(f"Error exporting todos: {str(e)}")
        flash('An error occurred while exporting tasks. Please try again.', 'error')
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(debug=False, host='0.0.0.0')

# Add WSGI application for cPanel
application = app
