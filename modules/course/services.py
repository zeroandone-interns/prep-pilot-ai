import json
from extensions import db, get_logger
from modules.shared.services.bedrock import BedrockService
from modules.shared.services.translation import TranslationService
from modules.document.entity import (
    Documents,
    Modules,
    Sections,
    Courses,
    Paragraphs,
    DocumentChunks,
)
from modules.course.prompts import GENERATE_MODULES_PROMPT


class CourseGenerationService:
    def __init__(self):
        self.bedrock = BedrockService()
        self.logger = get_logger()
        self.translation_service = TranslationService()

    def _translate_and_assign(self, text):
        if not text:
            return {"en": None, "fr": None, "ar": None}
        en, fr, ar = self.translation_service.translate_to_all_languages(text)
        return {"en": en, "fr": fr, "ar": ar}

    # Course Retrieval
    def _get_course_details(self, course_id):
        course_data = (
            Courses.query.with_entities(
                Courses.nb_of_modules,
                Courses.nb_of_sections,
                Courses.title,
                Courses.level,
                Courses.duration,
                Courses.description,
            )
            .filter_by(id=course_id)
            .first()
        )
        if not course_data:
            self.logger.error(f"Course with id {course_id} not found")
            raise ValueError(f"Course with id {course_id} not found")

        course_info = {
            "title": course_data.title,
            "description": course_data.description,
            "level": course_data.level,
            "duration": course_data.duration,
            "nb_of_modules": course_data.nb_of_modules,
            "nb_of_sections": course_data.nb_of_sections,
        }

        # self.logger.info(f"[_get_course_details] Retrieved course info: {course_info}")
        return course_info

    def _get_course_documents(self, course_id, embedding, top_k=10):
        chunks = (
            db.session.query(DocumentChunks)
            .join(Documents, DocumentChunks.document_id == Documents.id)
            .join(Courses, Documents.course_id == Courses.id)
            .filter(Courses.id == course_id)
            .order_by(DocumentChunks.embeddings_en.op("<=>")(embedding))
            .limit(top_k)
            .all()
        )

        # self.logger.info(
        #     f"[_get_course_documents] Retrieved {len(chunks)} chunks for course {course_id} by similarity"
        # )
        return chunks

    def _combine_course_content(self, documents):
        combined_text = "\n".join(doc.text_en for doc in documents if doc.text_en)
        # self.logger.info(
        #     f"[_combine_course_content] Combined course content: {combined_text[:500]}"
        # )
        return combined_text

    def _embed_course_info(self, course_info):
        text_to_embed = f"{course_info['title']}. {course_info['description']}"
        # self.logger.info(f"[_embed_course_info] Embedding text: {text_to_embed}")
        embedding = self.bedrock.generate_embedding(text_to_embed)
        return embedding

    # Bedrock Call Wrapper
    def bedrock_generate(self, prompt, max_tokens=10000, temperature=0.5):
        # self.logger.info(f"Calling Bedrock with prompt: {prompt}")
        try:
            response = self.bedrock.invoke_model_streaming(
                prompt,
                model_id="anthropic.claude-3-sonnet-20240229-v1:0",
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return json.loads(response)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode JSON response: {response}")
            return {}

    # Generators
    def _call_bedrock_for_modules(self, course_info, course_text):
        prompt = GENERATE_MODULES_PROMPT.format(
            title=course_info["title"],
            description=course_info["description"],
            level=course_info["level"],
            duration=course_info["duration"],
            nb_of_modules=course_info["nb_of_modules"],
            nb_of_sections=course_info["nb_of_sections"],
            content=course_text,
        )

        # self.logger.info(f"Generated prompt for modules: {prompt}")
        modules_data = self.bedrock_generate(prompt)

        if not isinstance(modules_data, list) or len(modules_data) == 0:
            self.logger.error("Bedrock did not return valid modules")
            return []
        return modules_data

    # Course Structure Generation

    # Course Structure Generation
    def generate_course_structure(self, course_id):

        course_info = self._get_course_details(course_id)
        embeddings = self._embed_course_info(course_info)
        chunks = self._get_course_documents(course_id, embeddings, top_k=10)
        course_text = self._combine_course_content(chunks)

        # Step 1: Generate modules + sections + paragraphs
        modules_data = self._call_bedrock_for_modules(course_info, course_text)
        self.logger.info(
            f"[generate_course_structure] Generated modules data: {modules_data}"
        )

        results = []

        # Step 2: Save modules, sections, paragraphs
        for module_data in modules_data:
            titles = self._translate_and_assign(module_data["title"])
            module_entity = Modules(
                title_en=titles["en"],
                title_fr=titles["fr"],
                title_ar=titles["ar"],
                course_id=course_id,
            )
            db.session.add(module_entity)
            db.session.flush()

            sections_list = []
            for section in module_data.get("sections", []):
                titles = self._translate_and_assign(section["title"])
                section_entity = Sections(
                    title_en=titles["en"],
                    title_fr=titles["fr"],
                    title_ar=titles["ar"],
                    module_id=module_entity.id,
                )
                db.session.add(section_entity)
                db.session.flush()

                paragraphs_list = []
                for para in section.get("paragraphs", []):
                    content_titles = self._translate_and_assign(para["content_title"])
                    content_bodyy = self._translate_and_assign(para["content_body"])
                    paragraph_entity = Paragraphs(
                        content_title_en=content_titles["en"],
                        content_body_en=content_bodyy["en"],
                        content_title_fr=content_titles["fr"],
                        content_body_fr=content_bodyy["fr"],
                        content_title_ar=content_titles["ar"],
                        content_body_ar=content_bodyy["ar"],
                        section_id=section_entity.id,
                    )
                    db.session.add(paragraph_entity)
                    db.session.flush()

                    paragraphs_list.append(
                        {
                            "content_title": para["content_title"],
                            "content_body": para["content_body"],
                        }
                    )

                sections_list.append(
                    {
                        "title": section["title"],
                        "paragraphs": paragraphs_list,
                    }
                )

            results.append({"module": module_data["title"], "sections": sections_list})

        db.session.commit()
        return results
