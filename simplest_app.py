from flask import Flask, render_template_string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test_secret_key'

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simplest App</title>
    </head>
    <body>
        <h1>Simplest Flask App</h1>
        <p>This page proves that basic Flask functionality works!</p>
    </body>
    </html>
    """)

if __name__ == '__main__':
    print("Starting most basic Flask app...")
    app.run(debug=True, port=5001)  # Using a different port just in case 