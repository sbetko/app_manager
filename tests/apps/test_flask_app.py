# apps/test_flask_app.py

from flask import Flask

app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello, Flask!"