import os
from modules.shared.services.s3 import S3Service
from modules.shared.services.bedrock import BedrockService
from modules.shared.services.transcrible import TranscribeService
from modules.shared.services.translation import TranslationService
from modules.document.prompts import TEXT_PROMPT, IMAGE_PROMPT
from modules.document.entity import Documents, DocumentChunks

from chonkie import SentenceChunker
from extensions import db, get_logger


 

class DocumentProcessingService:
    def __init__(self):
        self.s3_service = S3Service()
        self.bedrock_service = BedrockService()
        self.translate_service = TranslationService()
        self.transcribe_service = TranscribeService()
        self.logger = get_logger('[DocumentProcessingService]')

        self.IMAGE_TYPES = {
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
        }

        self.TEXT_TYPES = {
            "text/plain",
            "text/csv",
            "text/html",
            "application/json",
            "application/xml",
            "application/pdf",  # PDF
            "application/msword",  # .doc
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
        }

    def process_documents_for_course(self, s3_keys):
        self.logger.info(f"\nProcessing files: {s3_keys}")
        for s3_key in s3_keys:
            self.logger.info(f"\nProcessing file: {s3_key}")

            folder_name, file_name_with_extension = os.path.split(s3_key)
            self.logger.info(f"\nFolder name: {folder_name}, File name with extension: {file_name_with_extension}")

            file_name, file_extension = os.path.splitext(file_name_with_extension)
            self.logger.info(f"\nFile name: {file_name}, File extension: {file_extension}")

            doc_bytes, content_type = self.s3_service.read_file_from_s3(s3_key)

            if content_type in self.TEXT_TYPES:
                self.logger.info("\nText File Detected")
                self.logger.info("\nInvoking Bedrock for text extraction: 'invoke_document'")
                text = self.bedrock_service.invoke_document(
                    doc_bytes,
                    file_name,
                    file_extension,
                    TEXT_PROMPT,
                )
                self.logger.info(f"\nExtracted text successfully: \n====={text[:100]}...====")
                self.process_file(text, folder_name, s3_key)

            elif content_type in self.IMAGE_TYPES:
                self.logger.info("\nImage File Detected")
                self.logger.info("\nInvoking Bedrock for image extraction: 'invoke_image'")
                text = self.bedrock_service.invoke_image(
                    doc_bytes, content_type, IMAGE_PROMPT
                )
                self.logger.info(
                    f"\nExtracted text from image successfully: {text[:100]}..."
                )
                self.process_file(text, folder_name, s3_key)
            else:
                self.logger.info("\nVideo or Audio Detected")
                self.logger.info("\nInvoking Transcribe Service")
                text = self.transcribe_service.transcribe_file(
                    job_name=f"transcribe-{file_name}",
                    media_uri=f"s3://instructor-documents-store/{s3_key}",
                    media_format={file_extension},
                    language_code="en-US",
                )
                self.logger.info(f"\nTranscribed text successfully: {text[:100]}...")
                self.process_file(text, folder_name, s3_key)

    def process_file(self, text, course_id, s3_key):
        try:
            self.logger.info(f"\nProcessing file: {s3_key}")
            s3_uri = f"s3://{self.s3_service.head_bucket_name}/{s3_key}"

            self.logger.info("\nSaving in Documents table")
            document = self._save_document(course_id, s3_uri, text, type="ext")

            self.logger.info(f"\nChunking text for document: ID: {document.id}, Name: {document.s3_uri}")
            chunks = self._chunk_text(text)

            for chunk in chunks:
                text_en, text_fr, text_ar = (
                    self.translate_service.translate_to_all_languages(chunk["text"])
                )
                embedding_en = self.bedrock_service.generate_embedding(text_en)
                embedding_fr = self.bedrock_service.generate_embedding(text_fr)
                embedding_ar = self.bedrock_service.generate_embedding(text_ar)

                self._save_chunks(
                    document.id,
                    text_en=text_en,
                    text_fr=text_fr,
                    text_ar=text_ar,
                    embedding_en=embedding_en,
                    embedding_fr=embedding_fr,
                    embedding_ar=embedding_ar,
                    tokens=chunk["tokens"],
                )
            self.logger.info("\n===== PROCESSING COMPLETE =====\n\n")

        except Exception as e:
            self.logger.error(f"Error processing file {s3_key}: {e}")

    def _save_document(self, course_id, s3_uri, text, type):
        doc = Documents(
            course_id=course_id,
            s3_uri=s3_uri,
            language="en",
            text=text,
            type=type,
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

    def _save_chunks(
        self,
        document_id,
        text_en,
        text_fr,
        text_ar,
        embedding_en,
        embedding_fr,
        embedding_ar,
        tokens,
    ):
        chunk_entity = DocumentChunks(
            tokens=tokens,
            document_id=document_id,
            text_ar=text_ar,
            text_en=text_en,
            text_fr=text_fr,
            embeddings_ar=embedding_ar,
            embeddings_en=embedding_en,
            embeddings_fr=embedding_fr,
        )
        db.session.add(chunk_entity)

        db.session.commit()
