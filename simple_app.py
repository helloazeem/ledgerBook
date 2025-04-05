from flask import Flask, render_template, redirect, url_for, flash
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key')

# Simple routes without complex logic
@app.route('/')
def index():
    return render_template('simple_layout.html')

@app.route('/login')
def login():
    return render_template('simple_layout.html')

@app.route('/register')
def register():
    return render_template('simple_layout.html')

if __name__ == '__main__':
    app.run(debug=True, port=5002) 