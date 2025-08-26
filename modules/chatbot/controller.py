from flask import request, jsonify, Response
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


def chatbot_message_stream_controller():
    session_id = request.args.get("session_id")
    message = request.args.get("message")

    service = ChatbotService()
    if not session_id or not message:
        return jsonify({"error": "Missing required fields: session_id, message"}), 400

    return Response(
        service.handle_message_stream(session_id, message), mimetype="text/event-stream"
    )
