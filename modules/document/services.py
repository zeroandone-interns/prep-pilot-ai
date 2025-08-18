import os
from modules.shared.services.s3 import S3Service
from modules.shared.services.bedrock import BedrockService
from modules.shared.services.translation import TranslationService
from modules.document.prompts import image_prompt, text_prompt
from modules.document.entity import Documents, DocumentChunks

from chonkie import SentenceChunker
from extensions import db, get_logger


class DocumentProcessingService:
    def __init__(self):
        self.s3_service = S3Service()
        self.bedrock_service = BedrockService()
        self.translate_service = TranslationService()
        self.logger = get_logger()

    def process_documents_for_course(self, folder_name):
        folder_name = str(folder_name)
        bucket_exists = self.s3_service.check_if_bucket_exists()
        if not bucket_exists:
            self.logger.error(
                f"[S3] Bucket '{self.s3_service.head_bucket_name}' does not exist."
            )
            return

        folder_exists = self.s3_service.check_if_folder_exists(folder_name)
        if not folder_exists:
            self.logger.error(f"[S3] Folder '{folder_name}' does not exist.")
            return

        file_keys = self.s3_service.check_if_folder_has_files(folder_name)
        if not file_keys:
            self.logger.error(f"[S3] No files found in folder '{folder_name}'.")
            return

        self.logger.info(f"Processing file: {file_keys}")
        for file_key in file_keys[1:]:
            _, ext = os.path.splitext(file_key)
            self.logger.info(f"Processing file: {file_key} with extension: {ext}")
            ext = ext.lower()
            doc_bytes = self.s3_service.read_file_from_s3(file_key)

            if ext in [".pdf", ".docx", ".doc", ".txt", ".md", ".html"]:
                self.logger.info("processing with bedrock")
                text = self.bedrock_service.invoke_document(
                    doc_bytes,
                    file_key,
                    text_prompt,
                    ext,
                )
                self.logger.info(f"Extracted text successfully")
                self.process_file(text, ext, folder_name, file_key)

            elif ext in [".jpg", ".jpeg", ".png"]:
                text = self.bedrock_service.invoke_image(ext, image_prompt)
                self.process_file(text, ext, folder_name, file_key)
            else:
                raise ValueError(f"Unsupported text file type: {ext}")

    def process_file(self, text, ext, folder_name, file_key):
        try:
            self.logger.info(f"Processing file: {file_key} with extension: {ext}")
            s3_uri = f"s3://{self.s3_service.head_bucket_name}/{file_key}"

            self.logger.info("Saving in Documents table")
            # Save Documents in DB
            document = self._save_document(folder_name, s3_uri, text, ext)

            self.logger.info(f"Chunking text for document ID: {document.id}")
            chunks = self._chunk_text(text)
            self.logger.info(f"Number of chunks created: {len(chunks)}")

            for chunk in chunks:
                self.logger.info(f"Chunking text in for loop")
                # Translate the text into multiple languages
                text_en, text_fr, text_ar = (
                    self.translate_service.translate_to_all_languages(chunk["text"])
                )
                self.logger.info(f"Translated text successfully")
                embedding_en = self.bedrock_service.generate_embedding(text_en)
                embedding_fr = self.bedrock_service.generate_embedding(text_fr)
                embedding_ar = self.bedrock_service.generate_embedding(text_ar)

                # DocumentChunks(
                #     tokens=500,
                #     document_id=3,
                #     text_ar=text_ar,
                #     text_en=text_en,
                #     text_fr=text_fr,
                #     embedding_ar=embedding_ar,
                #     embedding_en=embedding_en,
                #     embedding_fr=embedding_fr,
                # )

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
            self.logger.info("PROCESSING COMPLETE")

        except Exception as e:
            self.logger.error(f"Error processing file {file_key}: {e}")

    def _save_document(self, course_id, s3_key, content_en, ext):
        doc = Documents(
            course_id=course_id,
            s3_key=s3_key,
            language="en",
            content_en=content_en,
            content_fr="content_fr",
            content_ar="content_ar",
            type=ext,
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
            # text='',
            text_ar=text_ar,
            text_en=text_en,
            text_fr=text_fr,
            embeddings_ar=embedding_ar,
            embeddings_en=embedding_en,
            embeddings_fr=embedding_fr,
        )
        db.session.add(chunk_entity)

        db.session.commit()
