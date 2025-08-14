import os
from modules.shared.services.s3 import S3Client
from modules.shared.services.bedrock import Bedrock
from modules.document.prompts import image_prompt
from modules.document.entity import Documents, DocumentChunks
from docx import Document as DocxDocument
from chonkie import SentenceChunker
from extensions import db
import pdfplumber


class DocumentProcessingService:
    def __init__(self):
        self.s3_service = S3Client()
        self.bedrock = Bedrock()

    def extract_text_from_pdf(self, file_path):
        full_text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        return full_text.strip()

    def extract_text_from_docx(self, file_path):
        doc = DocxDocument(file_path)
        return "\n".join(para.text for para in doc.paragraphs).strip()

    def extract_text_from_txt(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    def extract_text(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return self.extract_text_from_pdf(file_path)
        elif ext == ".docx":
            return self.extract_text_from_docx(file_path)
        elif ext == ".txt":
            return self.extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported text file type: {ext}")

    def analyze_image(self, file_path, image_prompt):
        return self.bedrock.invoke_image(file_path, image_prompt)

    def chunk_text(self, text, chunk_size=500, chunk_overlap=50):
        chunker = SentenceChunker(
            tokenizer_or_token_counter="gpt2",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_sentences_per_chunk=1,
        )
        chunks = chunker.chunk(text)
        return [{"text": c.text, "tokens": c.token_count} for c in chunks]

    def generate_embedding(self, text):
        return self.bedrock.generate_embedding(text)

    def save_document(self, course_id, s3_key, content, doc_type):
        doc = Documents(
            course_id=course_id,
            s3_key=s3_key,
            language="en",
            content_en=content,
            content_fr="content_fr",
            content_ar="content_ar",
            type=doc_type,
        )
        db.session.add(doc)
        db.session.commit()
        return doc

    def save_chunks(self, document_id, chunks):
        for chunk in chunks:
            embedding = self.generate_embedding(chunk["text"])
            chunk_entity = DocumentChunks(
                document_id=document_id,
                text=chunk["text"],
                tokens=chunk["tokens"],
                embeddings_en=embedding,
            )
            db.session.add(chunk_entity)
        db.session.commit()

    def process_text_document(self, course_id, s3_uri):
        downloaded_file = self.s3_service.download_file_from_s3_uri(s3_uri)
        try:
            text = self.extract_text(downloaded_file)
            doc_type = os.path.splitext(s3_uri)[1].lower()
            document = self.save_document(course_id, s3_uri, text, doc_type)
            chunks = self.chunk_text(text)
            self.save_chunks(document.id, chunks)
            return {"s3_key": s3_uri, "status": "processed"}
        finally:
            if downloaded_file and os.path.exists(downloaded_file):
                os.remove(downloaded_file)

    def process_image_document(self, course_id, s3_uri):
        downloaded_file = self.s3_service.download_file_from_s3_uri(s3_uri)
        try:
            content = self.analyze_image(downloaded_file, image_prompt)
            doc_type = os.path.splitext(s3_uri)[1].lower()
            document = self.save_document(course_id, s3_uri, content, doc_type)
            chunks = self.chunk_text(content)
            self.save_chunks(document.id, chunks)
            return {"s3_key": s3_uri, "status": "processed"}
        finally:
            if downloaded_file and os.path.exists(downloaded_file):
                os.remove(downloaded_file)

    def process_documents(self, course_id, documents):
        results = []
        for s3_uri in documents:
            if not isinstance(s3_uri, str):
                results.append(
                    {"s3_key": None, "error": "Each document must be an S3 URI string"}
                )
                continue
            ext = os.path.splitext(s3_uri)[1].lower()
            try:
                if ext in [".pdf", ".docx", ".txt"]:
                    result = self.process_text_document(course_id, s3_uri)
                elif ext in [".jpg", ".jpeg", ".png"]:
                    result = self.process_image_document(course_id, s3_uri)
                else:
                    result = {
                        "s3_key": s3_uri,
                        "error": f"Unsupported file extension: {ext}",
                    }
                results.append(result)
            except Exception as e:
                db.session.rollback()
                results.append({"s3_key": s3_uri, "error": str(e)})
        return results
