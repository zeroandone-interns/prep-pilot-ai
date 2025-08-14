from flask import Flask, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from dotenv import load_dotenv
from extensions import db
import os

load_dotenv()

app = Flask(__name__)

CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DB_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
migrate = Migrate(app, db)

from modules.document import routes as document_routes
from modules.chatbot import routes as chatbot_routes
# from modules.course import routes as course_routes

document_routes.register_document_routes(app)
chatbot_routes.register_chatbot_routes(app)
# course_routes.register_course_routes(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
