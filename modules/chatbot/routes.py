from flask import request
from modules.chatbot import controller


def register_chatbot_routes(app):
    app.add_url_rule(
        "/send_message",
        view_func=controller.chatbot_message_controller,
        methods=["POST"],
    )
    app.add_url_rule(
        "/send_message_stream",
        view_func=controller.chatbot_message_stream_controller,
        methods=["GET"],  # GET works better with EventSource
    )
