from flask import request, jsonify
from modules.chatbot.services import ChatbotService


def chatbot_message_controller():
    data = request.get_json()

    if not data or "session_id" not in data or "message" not in data:
        return jsonify({"error": "Missing required fields: session_id, message"}), 400

    service = ChatbotService()

    response_data = service.handle_message(
        session_id=data["session_id"], message=data["message"]
    )
    return jsonify(response_data)
