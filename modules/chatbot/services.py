from extensions import db
from langdetect import detect
from modules.shared.services.bedrock import BedrockService
from modules.chatbot.prompts import CHATBOT_RESPONSE_PROMPT
from modules.document.entity import (
    DocumentChunks,
    ChatMessage,
    Courses,
    ChatSession,
    User,
    Documents,
)


class ChatbotService:
    def __init__(self):
        self.bedrock = BedrockService()

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

    def get_chat_history(self, session_id, limit=10):
        history = (
            ChatMessage.query.filter_by(session_id=session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(history))

    def detect_language(self, text: str) -> str:
        try:
            lang = detect(text)
            print(f"Detected language: {lang}")
        except:
            lang = "en"

        if lang.startswith("fr"):
            return "fr"
        elif lang.startswith("ar"):
            return "ar"
        else:
            return "en"

    def get_user_org_id_from_session(self, session_id: int):
        return (
            db.session.query(User.organization_id)
            .join(ChatSession, ChatSession.user_id == User.id)
            .filter(ChatSession.id == session_id)
            .scalar()
        )

    def retrieve_similar_chunks(self, embedding, session_id, lang="en", top_k=10):
        user_org_id = self.get_user_org_id_from_session(session_id)
        print(f"User organization ID: {user_org_id}")
        if not user_org_id:
            return []

        embedding_column = {
            "en": DocumentChunks.embeddings_en,
            "fr": DocumentChunks.embeddings_fr,
            "ar": DocumentChunks.embeddings_ar,
        }[lang]

        return (
            db.session.query(DocumentChunks)
            .join(Documents, DocumentChunks.document_id == Documents.id)
            .join(Courses, Documents.course_id == Courses.id)
            .filter(Courses.organizationId == user_org_id)
            .order_by(embedding_column.op("<=>")(embedding))
            .limit(top_k)
            .all()
        )

    def generate_response(self, message, history, retrieved_chunks):
        context_text = "\n".join(chunk.text_en for chunk in retrieved_chunks)
        history_text = "\n".join(f"{msg.sender}: {msg.message}" for msg in history)

        prompt = CHATBOT_RESPONSE_PROMPT.format(
            context=context_text, history=history_text, message=message
        )

        print("Generated prompt:", prompt)

        return self.bedrock.invoke_model_with_text(
            prompt, temperature=0.5, max_tokens=4608
        )

    def handle_message(self, session_id, message):
        self.save_message(session_id, message, "User")

        lang = self.detect_language(message)
        embedding = self.bedrock.generate_embedding(message)

        history = self.get_chat_history(session_id)

        retrieved_chunks = self.retrieve_similar_chunks(
            embedding, session_id, lang=lang
        )

        response_text = self.generate_response(message, history, retrieved_chunks)

        self.save_message(session_id, response_text, "Assistant")

        return response_text
