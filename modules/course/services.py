import json
from extensions import db
from modules.shared.services.bedrock import Bedrock
from modules.document.entity import Documents, DocumentChunks
from modules.document.entity import Modules, Sections, FlashCards, Questions, Courses


class CourseContentService:
    def __init__(self):
        self.bedrock = Bedrock()

    def get_course_details(self, course_id):
        course = Courses.query.filter_by(id=course_id).first()
        if not course:
            raise ValueError(f"Course with id {course_id} not found")
        return course

    def get_course_documents(self, course_id):
        return Documents.query.filter_by(course_id=course_id).all()

    def combine_course_content(self, documents):
        return "\n".join(doc.content for doc in documents if doc.content)

    def bedrock_generate(self, prompt):
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "temperature": 0.5,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
        }
        response = self.bedrock.client.invoke_model(
            modelId=self.bedrock.model_id,
            contentType="application/json",
            body=json.dumps(request_body),
        )
        model_response = json.loads(response["body"].read())
        return model_response["content"][0]["text"]

    def generate_modules(self, course, course_text):
        prompt = f"""
        The course is titled '{course.title}' and has the following description: {course.description}.
        Based on the content below, split it into exactly {course.nb_of_modules} high-level modules.
        For each module, provide a short title and a paragraph summary.

        Content:
        {course_text}

        Respond in JSON format:
        [
          {{"title": "Module 1 Title", "summary": "Summary text"}},
          ...
        ]
        """
        return json.loads(self.bedrock_generate(prompt))

    def generate_sections(self, module_summary, nb_of_sections):
        prompt = f"""
        Create exactly {nb_of_sections} sections from the following module content:
        {module_summary}

        Each section should have a title and a short paragraph describing it.

        Respond in JSON format:
        [
          {{"title": "Section 1 Title", "summary": "Section summary"}},
          ...
        ]
        """
        return json.loads(self.bedrock_generate(prompt))

    def generate_flashcards(self, module_summary):
        prompt = f"""
        Create exactly 3 flashcards summarizing the following module:
        {module_summary}

        Respond in JSON format:
        [
          {{"front": "Front text", "back": "Back text"}},
          ...
        ]
        """
        return json.loads(self.bedrock_generate(prompt))

    def generate_questions(self, module_summary):
        prompt = f"""
        Create exactly 3 multiple-choice questions (MCQs) from the following module:
        {module_summary}

        Each question must have 3 options, 1 correct answer, and an explanation.

        Respond in JSON format:
        [
          {{
            "question": "Question text",
            "options": ["Option 1", "Option 2", "Option 3"],
            "correct_answer": "Option 2",
            "explanation": "Why this is correct"
          }},
          ...
        ]
        """
        return json.loads(self.bedrock_generate(prompt))

    def generate_course_structure(self, course_id):
        course = self.get_course_details(course_id)
        documents = self.get_course_documents(course_id)
        course_text = self.combine_course_content(documents)

        modules_data = self.generate_modules(course, course_text)
        results = []

        for module_data in modules_data:
            # Save module
            module_entity = Modules(title=module_data["title"], course_id=course_id)
            db.session.add(module_entity)
            db.session.flush()  # get module id

            # Sections
            sections_data = self.generate_sections(
                module_data["summary"], course.nb_of_sections
            )
            for section in sections_data:
                section_entity = Sections(
                    title=section["title"],
                    module_id=module_entity.id,
                    is_complete=False,
                )
                db.session.add(section_entity)

            # Flashcards
            flashcards_data = self.generate_flashcards(module_data["summary"])
            for fc in flashcards_data:
                flashcard_entity = FlashCards(
                    module_id=module_entity.id, front_1=fc["front"], back_1=fc["back"]
                )
                db.session.add(flashcard_entity)

            # Questions
            questions_data = self.generate_questions(module_data["summary"])
            for q in questions_data:
                question_entity = Questions(
                    section_id=None,  # optional: link to a specific section if needed
                    question_text=q["question"],
                    option1=q["options"][0],
                    option2=q["options"][1],
                    option3=q["options"][2],
                    correct_answer=q["correct_answer"],
                    explanation=q["explanation"],
                )
                db.session.add(question_entity)

            results.append(
                {
                    "module": module_data["title"],
                    "sections": sections_data,
                    "flashcards": flashcards_data,
                    "questions": questions_data,
                }
            )

        db.session.commit()
        return results
