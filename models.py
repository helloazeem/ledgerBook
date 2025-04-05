from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import enum

# Initialize SQLAlchemy here, it will be configured in app.py
db = SQLAlchemy()

# Many-to-many relationship between users and companies
user_company = db.Table('user_company',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('company_id', db.Integer, db.ForeignKey('company_settings.id'), primary_key=True)
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    companies = db.relationship('CompanySettings', secondary=user_company, backref=db.backref('users', lazy='dynamic'))
    todos = db.relationship('Todo', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    
    # Current active company for this user
    active_company_id = db.Column(db.Integer, db.ForeignKey('company_settings.id'), nullable=True)
    active_company = db.relationship('CompanySettings', foreign_keys=[active_company_id])

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def __repr__(self):
        return f'<User {self.username}>'

class CompanySettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    logo_path = db.Column(db.String(200), nullable=True)
    next_invoice_number = db.Column(db.Integer, default=1001)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    clients = db.relationship('Client', backref='company', lazy='dynamic', cascade="all, delete-orphan")

    @classmethod
    def get_settings(cls, company_id=None):
        # If company_id is provided, get that specific company
        if company_id:
            settings = cls.query.get(company_id)
        else:
            # Return the first (and should be only) settings object, or create if none exists
            settings = cls.query.first()
            
        if not settings:
            settings = cls(name="My Company")
            db.session.add(settings)
            db.session.commit()
        return settings
        
    def get_next_invoice_number(self):
        invoice_num = self.next_invoice_number
        self.next_invoice_number += 1
        db.session.commit()
        return invoice_num

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company_settings.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Use string reference for Transaction to avoid circular import if models grow
    # Use lazy='dynamic' to get a query object for transactions, allowing further filtering/ordering
    transactions = db.relationship('Transaction', backref='client', lazy='dynamic', cascade="all, delete-orphan", order_by='Transaction.date, Transaction.id') # Order transactions by date then ID

    def __repr__(self):
        return f'<Client {self.name}>'

    # Helper property to get the latest balance
    @property
    def current_balance(self):
        # Need to reference Transaction explicitly here
        # Order by date DESC then ID DESC to get the absolute latest
        latest_transaction = self.transactions.order_by(Transaction.date.desc(), Transaction.id.desc()).first()
        return latest_transaction.balance if latest_transaction else 0.0
    
    # Helper method to count overdue transactions
    def count_overdue_transactions(self):
        today = datetime.now().date()
        overdue_count = Transaction.query.filter(
            Transaction.client_id == self.id,
            Transaction.due_date.isnot(None),  # Ensure due_date exists
            Transaction.due_date < datetime.now(),  # Compare datetime to datetime
            Transaction.is_paid == False,
            Transaction.debit > 0
        ).count()
        return overdue_count

class TransactionStatus(enum.Enum):
    PENDING = 'pending'
    PAID = 'paid'
    OVERDUE = 'overdue'
    CANCELLED = 'cancelled'

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    invoice_number = db.Column(db.String(20), nullable=True, unique=True)
    reference = db.Column(db.String(50), nullable=True)  # For external reference numbers
    # Use DateTime for flexibility, though we might only use the date part initially
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)  # Optional due date for invoices
    description = db.Column(db.String(200), nullable=False)
    debit = db.Column(db.Float, nullable=True) # Amount owed by client increases
    credit = db.Column(db.Float, nullable=True) # Amount paid by client or credit given
    balance = db.Column(db.Float, nullable=False) # Running balance *after* this transaction
    is_paid = db.Column(db.Boolean, default=False)  # Whether invoice has been paid
    status = db.Column(db.String(20), default=TransactionStatus.PENDING.value)  # Transaction status
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Transaction {self.id} for Client {self.client_id} on {self.date.strftime("%Y-%m-%d")}>'
    
    def update_status(self):
        today = datetime.now().date()
        
        if self.credit and not self.debit:
            # Payment made
            self.status = TransactionStatus.PAID.value
            return
            
        if self.debit and not self.is_paid:
            if self.due_date and self.due_date.date() < today:
                self.status = TransactionStatus.OVERDUE.value
            else:
                self.status = TransactionStatus.PENDING.value
        elif self.is_paid:
            self.status = TransactionStatus.PAID.value
        
        return self.status

class TodoPriority(enum.Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    priority = db.Column(db.String(20), default=TodoPriority.MEDIUM.value)
    is_completed = db.Column(db.Boolean, default=False)
    position = db.Column(db.Integer, default=0)  # For ordered todos
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Todo {self.id}: {self.title}>'
    
    @property
    def is_overdue(self):
        if self.due_date and not self.is_completed:
            return self.due_date.date() < datetime.now().date()
        return False 