import json, uuid
from modules.shared.services.bedrock import Bedrock
from modules.document.entity import DocumentChunk, ChatMessage
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
            id=str(uuid.uuid4()),
            message=message,
            sender=sender,
            session_id=session_id,
        )
        db.session.add(msg)
        db.session.commit()
        return msg

    def generate_embedding(self, text):
        payload = {"inputText": text}
        response = self.bedrock.client.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )
        result = response["body"].read()
        return json.loads(result)["embedding"]

    def get_chat_history(self, session_id, limit=10):
        history = (
            ChatMessage.query.filter_by(session_id=session_id)
            .order_by(ChatMessage.createdAt.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(history))

    def retrieve_similar_chunks(self, embedding, top_k=5):
        return (
            db.session.query(DocumentChunk)
            .order_by(DocumentChunk.embeddings.op("<=>")(embedding))
            .limit(top_k)
            .all()
        )

    def generate_response(self, message, history, retrieved_chunks):
        context_text = "\n".join(chunk.text for chunk in retrieved_chunks)
        history_text = "\n".join(f"{msg.sender}: {msg.message}" for msg in history)

        prompt = f"""You are an expert AI assistant that answers questions by carefully using ONLY the information provided in the context and chat history below.

        Relevant context:
        {context_text}

        Chat history:
        {history_text}

        User message:
        {message}

        Please follow these rules when answering:
        1. Use ONLY the Context and Chat History to answer. Do NOT add any information that is not supported by these.
        2. If the Context does not contain enough information to answer, reply politely:
        "I'm sorry, I don't have enough information to answer that."
        3. Provide clear, concise, and easy-to-understand answers.
        4. Avoid special words or expressions unless the user uses it first.
        5. Be polite and helpful at all times.

        Provide the best possible answer based on the context and history.
        Answer:
        """

        print("Generated prompt:", prompt)

        native_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "temperature": 0.5,
            "max_tokens": 1536,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = self.bedrock.client.invoke_model(
            modelId=self.bedrock.model_id,
            contentType="application/json",
            body=json.dumps(native_request),
        )

        model_response = json.loads(response["body"].read())
        return model_response["content"][0]["text"]

    def handle_message(self, session_id, message):
        print("Handling message for session:", session_id)

        self.save_message(session_id, message, "User")
        print("Received message:", message)

        embedding = self.generate_embedding(message)
        print("Generated embedding:", embedding)

        history = self.get_chat_history(session_id)
        print("Retrieved chat history:", history)

        retrieved_chunks = self.retrieve_similar_chunks(embedding)
        print("Retrieved similar chunks:", retrieved_chunks)

        response_text = self.generate_response(message, history, retrieved_chunks)
        print("Generated response:", response_text)

        self.save_message(session_id, response_text, "Assistant")
        print("Saved assistant response to database")

        return response_text
