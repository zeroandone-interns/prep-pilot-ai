import os
from modules.shared.services.s3 import S3Service
from modules.shared.services.bedrock import Bedrock
from modules.document.prompts import image_prompt, text_prompt
from modules.document.entity import Documents, DocumentChunks
from modules.shared.services.translation import TranslationService
from chonkie import SentenceChunker
from extensions import db


class DocumentProcessingService:
    def __init__(self):
        self.s3_service = S3Service()
        self.bedrock_service = Bedrock()
        self.translate_service = TranslationService()


    def process_documents_for_course(self, bucket_name="34324"):
        bucket_exists = self.s3_service.check_if_bucket_exists()
        if not bucket_exists:
            self.logger.error(f"[S3] Bucket '{bucket_name}' does not exist.")
            return
        
        folder_exists = self.s3_service.check_if_folder_exists(bucket_name)
        if not folder_exists:
            self.logger.error(f"[S3] Folder '{bucket_name}' does not exist.")
            return
        
        file_keys = self.s3_service.check_if_folder_has_files(bucket_name)
        if not file_keys:
            self.logger.error(f"[S3] No files found in folder '{bucket_name}'.")
            return

        for file_key in file_keys:
            file_name, ext = os.path.splitext(file_key)
            ext = ext.lower()
            if ext == ".pdf" or ext == ".docx" or ext == ".txt" or ext == ".md":
                text = self.bedrock_service.invoke_model_with_text(ext, text_prompt)
                self.process_file(text, ext, bucket_name, file_key)
            elif ext in [".jpg", ".jpeg", ".png"]:
                text = self.bedrock_service.invoke_image(ext, image_prompt)
                self.process_file(text, ext, bucket_name, file_key)
            else:
                raise ValueError(f"Unsupported text file type: {ext}")



    def process_file(self, text, ext, bucket_name, file_key):
        s3_uri = f"s3://{self.s3_service.head_bucket_name}/{bucket_name}/{file_key}"
        # Translate the text into multiple languages
        content_en, content_fr, content_ar = (
                self.translate_service.translate_to_all_languages(text)
            )
        # Save Documents in DB
        document = self._save_document(
                bucket_name, s3_uri, content_en, content_fr, content_ar, ext
            )
        # Chunk the text into smaller pieces
        chunks = self._chunk_text(text)
        # Save Chunks in DB
        self._save_chunks(document.id, chunks)
        return {"s3_key": s3_uri, "status": "processed"}
           



    def _save_document(
        self, course_id, s3_key, content_en, content_fr, content_ar, doc_type
    ):
        doc = Documents(
            course_id=course_id,
            s3_key=s3_key,
            language="en",
            content_en=content_en,
            content_fr=content_fr,
            content_ar=content_ar,
            type=doc_type,
        )
        db.session.add(doc)
        db.session.commit()
        return doc

    def _chunk_text(self, text, chunk_size=500, chunk_overlap=50):
        chunker = SentenceChunker(
            tokenizer_or_token_counter="gpt2",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_sentences_per_chunk=1,
        )
        chunks = chunker.chunk(text)
        return [{"text": c.text, "tokens": c.token_count} for c in chunks]


    def _save_chunks(self, document_id, chunks):
        for chunk in chunks:
            embedding = self.bedrock_service.generate_embedding(chunk["text"])
            chunk_entity = DocumentChunks(
                document_id=document_id,
                text=chunk["text"],
                tokens=chunk["tokens"],
                embeddings_en=embedding,
            )
            db.session.add(chunk_entity)
        db.session.commit()


