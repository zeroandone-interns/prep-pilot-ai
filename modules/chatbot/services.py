import json
from modules.shared.services.bedrock import Bedrock
from modules.document.entity import DocumentChunks, ChatMessage
from modules.chatbot.prompts import CHATBOT_RESPONSE_PROMPT
from extensions import db


class ChatbotService:
    def __init__(self):
        self.bedrock = Bedrock()

    def validate_request(self, data):
        if not data:
            return False, "No JSON payload provided"
        if "session_id" not in data or "message" not in data:
            return False, "Missing required fields: session_id, message"
        return True, None

    def save_message(self, session_id, message, sender):
        msg = ChatMessage(
            message=message,
            sender=sender,
            session_id=session_id,
        )
        db.session.add(msg)
        db.session.commit()
        return msg

    def generate_embedding(self, text):
        return self.bedrock.generate_embedding(text)

    def get_chat_history(self, session_id, limit=10):
        history = (
            ChatMessage.query.filter_by(session_id=session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(history))

    def retrieve_similar_chunks(self, embedding, top_k=5):
        return (
            db.session.query(DocumentChunks)
            .order_by(DocumentChunks.embeddings_en.op("<=>")(embedding))
            .limit(top_k)
            .all()
        )

    def generate_response(self, message, history, retrieved_chunks):
        context_text = "\n".join(chunk.text for chunk in retrieved_chunks)
        history_text = "\n".join(f"{msg.sender}: {msg.message}" for msg in history)

        prompt = CHATBOT_RESPONSE_PROMPT.format(
            context=context_text, history=history_text, message=message
        )

        print("Generated prompt:", prompt)

        return self.bedrock.invoke_model_with_text(
            prompt, temperature=0.5, max_tokens=1536
        )

    def handle_message(self, session_id, message):
        self.save_message(session_id, message, "User")

        embedding = self.generate_embedding(message)
        history = self.get_chat_history(session_id)
        retrieved_chunks = self.retrieve_similar_chunks(embedding)

        response_text = self.generate_response(message, history, retrieved_chunks)

        self.save_message(session_id, response_text, "Assistant")

        return response_text
