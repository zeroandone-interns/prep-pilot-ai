import json
from extensions import db, get_logger
from modules.shared.services.bedrock import BedrockService
from modules.document.entity import (
    Documents,
    Modules,
    Sections,
    Courses,
    Paragraphs,
    Questions,
    DocumentChunks,
)
from modules.course.prompts import (
    GENERATE_MODULES_PROMPT,
    GENERATE_QUESTIONS_PROMPT,
)


class CourseGenerationService:
    def __init__(self):
        self.bedrock = BedrockService()
        self.logger = get_logger()

    # Course Retrieval
    def _get_course_details(self, course_id):
        course_data = (
            Courses.query.with_entities(
                Courses.nb_of_modules,
                Courses.nb_of_sections,
                Courses.title,
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
            "nb_of_modules": course_data.nb_of_modules,
            "nb_of_sections": course_data.nb_of_sections,
        }

        self.logger.info(f"Retrieved course info: {course_info}")
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

        self.logger.info(
            f"Retrieved {len(chunks)} chunks for course {course_id} by similarity"
        )
        return chunks

    def _combine_course_content(self, documents):
        combined_text = "\n".join(doc.text_en for doc in documents if doc.text_en)
        self.logger.info(f"Combined course content: {combined_text}")
        return combined_text

    def _embed_course_info(self, course_info):
        text_to_embed = f"{course_info['title']}. {course_info['description']}"
        self.logger.info(f"Embedding text: {text_to_embed}")
        embedding = self.bedrock.generate_embedding(text_to_embed)
        return embedding

    # Bedrock Call Wrapper

    def bedrock_generate(self, prompt, max_tokens=10000, temperature=0.5):
        self.logger.info(f"Calling Bedrock with prompt: {prompt}")
        response = self.bedrock.invoke_model_streaming(
            prompt, temperature=temperature, max_tokens=max_tokens
        )
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode JSON response: {response}")
            return {}

    # Generators

    def _call_bedrock_for_modules(self, course_info, course_text):
        prompt = GENERATE_MODULES_PROMPT.format(
            title=course_info["title"],
            description=course_info["description"],
            nb_of_modules=course_info["nb_of_modules"],
            nb_of_sections=course_info["nb_of_sections"],
            content=course_text,
        )
        self.logger.info(f"Generated prompt for modules: {prompt}")
        modules_data = self.bedrock_generate(prompt)

        if not isinstance(modules_data, list) or len(modules_data) == 0:
            self.logger.error("Bedrock did not return valid modules")
            return []
        return modules_data

    def _call_bedrock_for_questions(self, content):
        prompt = GENERATE_QUESTIONS_PROMPT.format(module_summary=content)
        questions_data = self.bedrock_generate(prompt)
        if not isinstance(questions_data, list) or len(questions_data) == 0:
            self.logger.error("Bedrock did not return valid questions")
            return []
        return questions_data

    # Course Structure Generation
    def generate_course_structure(self, course_id):
        course_info = self._get_course_details(course_id)
        embeddings = self._embed_course_info(course_info)
        chunks = self._get_course_documents(course_id, embeddings, top_k=10)
        course_text = self._combine_course_content(chunks)

        # Step 1: Generate modules + sections + paragraphs
        modules_data = self._call_bedrock_for_modules(course_info, course_text)
        self.logger.info(f"Generated modules data: {modules_data}")

        results = []

        # Step 2: Save modules, sections, paragraphs
        for module_data in modules_data:
            module_entity = Modules(title=module_data["title"], course_id=course_id)
            db.session.add(module_entity)
            db.session.flush()

            sections_list = []
            for section in module_data.get("sections", []):
                section_entity = Sections(
                    title=section["title"],
                    module_id=module_entity.id,
                    # is_complete=False,
                )
                db.session.add(section_entity)
                db.session.flush()

                paragraphs_list = []
                for para in section.get("paragraphs", []):
                    paragraph_entity = Paragraphs(
                        content_title=para["content_title"],
                        content_body=para["content_body"],
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

    # Questions Generation
    def _get_section_paragraphs(self, section_id):
        paragraphs = Paragraphs.query.filter_by(section_id=section_id).all()
        self.logger.info(
            f"Fetched {len(paragraphs)} paragraphs for section {section_id}"
        )
        if not paragraphs:
            self.logger.warning(f"No paragraphs found for section {section_id}")
            return ""
        combined_text = "\n".join(
            [p.content_body for p in paragraphs if p.content_body]
        )
        return combined_text

    def _save_questions_to_db(self, section_id, questions_data):
        self.logger.info(f"Saving {questions_data} questions for section {section_id}")
        saved_questions = []
        for q in questions_data:
            try:
                question_entity = Questions(
                    section_id=section_id,
                    question_text=q.get("question"),
                    option1=q.get("options", [None, None, None])[0],
                    option2=q.get("options", [None, None, None])[1],
                    option3=q.get("options", [None, None, None])[2],
                    correct_answer=q.get("correct_answer"),
                    explanation=q.get("explanation"),
                )
                db.session.add(question_entity)
                db.session.flush()

                saved_questions.append(
                    {
                        "id": question_entity.id,
                        "question": question_entity.question_text,
                        "options": [
                            question_entity.option1,
                            question_entity.option2,
                            question_entity.option3,
                        ],
                        "correct_answer": question_entity.correct_answer,
                        "explanation": question_entity.explanation,
                    }
                )
            except Exception as e:
                self.logger.error(
                    f"Error saving question for section {section_id}: {e}"
                )

        db.session.commit()
        return saved_questions

    # Main Quiz Generation
    def generate_quiz(self, section_id):
        # Combine content
        combined_text = self._get_section_paragraphs(section_id)
        if not combined_text:
            return []

        # Generate questions via Bedrock
        questions_data = self._call_bedrock_for_questions(combined_text)
        if not questions_data:
            return []

        # Save and return
        return self._save_questions_to_db(section_id, questions_data)
