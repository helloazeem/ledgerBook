from app import app, db
from models import Client, Transaction

# This script fixes balance calculation issues
# It updates the 'balance' field in all transactions to maintain correct running totals

def recalculate_client_balances():
    print("Starting balance recalculation...")
    
    with app.app_context():
        # Get all clients
        clients = Client.query.all()
        print(f"Found {len(clients)} clients")
        
        for client in clients:
            print(f"Processing client: {client.name}")
            
            # Sort transactions by date and ID
            transactions = client.transactions.order_by(Transaction.date, Transaction.id).all()
            
            # Recalculate running balance
            running_balance = 0
            for tx in transactions:
                if tx.debit:
                    running_balance += tx.debit
                if tx.credit:
                    running_balance -= tx.credit
                
                # Update the balance field
                tx.balance = running_balance
                print(f"  - Updated transaction {tx.id}: {tx.description}, balance: {tx.balance}")
            
            # Commit changes for this client
            db.session.commit()
            print(f"Updated {len(transactions)} transactions for {client.name}")
            
        print("Balance recalculation completed!")

if __name__ == "__main__":
    recalculate_client_balances() 