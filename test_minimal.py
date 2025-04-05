from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def hello():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test App</title>
    </head>
    <body>
        <h1>Hello World!</h1>
        <p>If you can see this, Flask is working correctly.</p>
    </body>
    </html>
    """)

if __name__ == '__main__':
    app.run(debug=True) 