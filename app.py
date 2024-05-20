from flask import Flask
from flask_cors import CORS
import logging
from routes import setup_routes

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)
setup_routes(app)  

if __name__ == "__main__":
    app.run(debug=True, port=5001)
