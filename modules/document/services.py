import os

from flask import json
from modules.shared.services.s3 import S3Service
from modules.shared.services.bedrock import BedrockService
from modules.shared.services.transcrible import TranscribeService
from modules.shared.services.translation import TranslationService
from modules.document.prompts import TEXT_PROMPT, IMAGE_PROMPT
from modules.document.entity import Courses, Documents, DocumentChunks

from chonkie import SemanticChunker, SentenceChunker
from extensions import db, get_logger


class DocumentProcessingService:
    def __init__(self):
        self.s3_service = S3Service()
        self.bedrock_service = BedrockService()
        self.translate_service = TranslationService()
        self.transcribe_service = TranscribeService()
        self.logger = get_logger("[DocumentProcessingService]")
        self.chunk_size = 2048
        self.context_window = 160000

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

        self.VIDEO_AUDIO_TYPES = {
            "video/mp4",
            "video/webm",
            "video/ogg",
            "audio/mpeg",
            "audio/wav",
            "audio/ogg",
        }

    def process_documents_for_course(self, s3_keys):
        self.logger.info(f"[process_documents_for_course] Processing files: {s3_keys}")
        for s3_key in s3_keys:
            self.logger.info(f"[process_documents_for_course] Processing file: {s3_key}")

            folder_name, file_name_with_extension = os.path.split(s3_key)
            self.logger.debug(
                f"[process_documents_for_course] Folder name: {folder_name}, File name with extension: {file_name_with_extension}"
            )

            file_name, file_extension = os.path.splitext(file_name_with_extension)
            self.logger.debug(
                f"[process_documents_for_course] File name: {file_name}, File extension: {file_extension}"
            )

            doc_bytes, content_type = self.s3_service.read_file_from_s3(s3_key)

            if content_type in self.TEXT_TYPES:
                self.logger.info("[process_documents_for_course] Text File Detected")
                self.logger.info(
                    "[process_documents_for_course] Invoking Bedrock for text extraction: 'invoke_document'"
                )
                text = self.bedrock_service.invoke_document(
                    doc_bytes,
                    file_name,
                    file_extension,
                    TEXT_PROMPT,
                )

                self.logger.info(
                    f"\n[process_documents_for_course] ====={text}===="
                )
                return self.process_file(text, folder_name, s3_key)
            elif content_type in self.IMAGE_TYPES:
                self.logger.info("[process_documents_for_course] Image File Detected")
                self.logger.info(
                    "\n[process_documents_for_course] Invoking Bedrock for image extraction: 'invoke_image'"
                )
                text = self.bedrock_service.invoke_image(
                    doc_bytes, content_type, IMAGE_PROMPT
                )
                self.logger.info(
                    f"\n[process_documents_for_course] Extracted text from image successfully: {text}"
                )
                return self.process_file(text, folder_name, s3_key)
            elif content_type in self.VIDEO_AUDIO_TYPES:
                self.logger.info("[process_documents_for_course] Video or Audio Detected")
                self.logger.info("[process_documents_for_course] Invoking Transcribe Service")
                text = self.transcribe_service.transcribe_file(
                    job_name=f"transcribe-{file_name}",
                    media_uri=f"s3://instructor-documents-store/{s3_key}",
                    media_format={file_extension},
                    language_code="en-US",
                )
                self.logger.info(f"\n[process_documents_for_course] Transcribed text successfully: {text[:100]}...")
                return self.process_file(text, folder_name, s3_key)
            else:
                raise ValueError(f"Unsupported content type: {content_type}")

    def process_file(self, text, course_id, s3_key):
        try:
            self.logger.info(f"[process_file] Processing file: {s3_key}")
            s3_uri = f"s3://{self.s3_service.head_bucket_name}/{s3_key}"

            if isinstance(text, str):
                try:
                    parsed_text = json.loads(text)
                except json.JSONDecodeError as e:
                    self.logger.error(f"[process_file] Failed to parse JSON: {e}")
                    parsed_text = {"extracted_text": text, "key_terms": []}
            else:
                parsed_text = text

            self.logger.info(f"[process_file] Save key terms in Course {course_id}")
            course = self._get_course(course_id)
            existing_terms = course.terms if course.terms else []
            new_terms = []
            
            for term in parsed_text.get("key_terms", []):
                if term not in existing_terms:
                    new_terms.append(term)

            if new_terms:
                all_terms = existing_terms + new_terms
                course.terms = all_terms
                db.session.commit()
            
            self.logger.info("[process_file] Saving in Documents table")
            document = self._save_document(course_id, s3_uri, parsed_text.get("extracted_text", ""))

            self.logger.info(
                f"[process_file] Chunking text for document: ID: {document.id}, Name: {document.s3_uri}"
            )
            chunks = self._chunk_text(parsed_text.get("extracted_text", ""))

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
            
            return True

        except Exception as e:
            self.logger.error(f"[process_file] Error processing file {s3_key}: {e}")
            return False

    def _save_document(self, course_id, s3_uri, text):
        doc = Documents(
            course_id=course_id,
            s3_uri=s3_uri,
            text=text,
        )
        db.session.add(doc)
        db.session.commit()
        return doc

    def _chunk_text(self, text):
        if not isinstance(text, str):
            raise ValueError("Text input must be a string for chunking")
            
        chunker = SentenceChunker(
            tokenizer_or_token_counter="gpt2",
            chunk_size=500,
            chunk_overlap=50,
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

    def _get_course(self, course_id):
        return Courses.query.filter_by(id=course_id).first()