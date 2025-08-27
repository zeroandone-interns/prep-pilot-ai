from flask import Flask, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from extensions import db
from modules.shared.services.secrets import SecretsDBService

from modules.flashcard.service import FlashcardService

# from modules.flashcard.service import FlashcardService


app = Flask(__name__)
CORS(app)

secrets_db = SecretsDBService()

app.config["SQLALCHEMY_DATABASE_URI"] = secrets_db.get_db_url()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
migrate = Migrate(app, db)

# Import and register routes
from modules.document import routes as document_routes
from modules.chatbot import routes as chatbot_routes
from modules.course import routes as course_routes

document_routes.register_document_routes(app)
chatbot_routes.register_chatbot_routes(app)
course_routes.register_course_routes(app)


# ############################
flashcard_service = FlashcardService()
from extensions import get_logger

logger = get_logger("[FlashcardAPI]")


@app.route("/flashcards", methods=["GET"])
def get_flashcards():
    try:
        flashcards = flashcard_service.generate_flashcard(1)
        return jsonify({"flashcards": flashcards}), 200
    except Exception as e:
        logger.error(f"Error retrieving flashcards: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500


# ########################

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
