import json
from extensions import db
from modules.shared.services.bedrock import Bedrock
from modules.document.entity import Documents, DocumentChunks
from modules.document.entity import Modules, Sections, FlashCards, Questions, Courses
from modules.course.prompts import (
    GENERATE_MODULES_PROMPT,
    GENERATE_SECTIONS_PROMPT,
    GENERATE_FLASHCARDS_PROMPT,
    GENERATE_QUESTIONS_PROMPT,
)


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
        return "\n".join(doc.content_en for doc in documents if doc.content_en)

    def bedrock_generate(self, prompt, max_tokens=10000, temperature=0.5):
        return self.bedrock.invoke_model_with_text(
            prompt, temperature=temperature, max_tokens=max_tokens
        )

    def generate_modules(self, course, course_text):
        prompt = GENERATE_MODULES_PROMPT.format(
            title=course.title,
            description=course.description,
            nb_of_modules=course.nb_of_modules,
            content=course_text,
        )
        return json.loads(self.bedrock_generate(prompt))

    def generate_sections(self, module_summary, nb_of_sections):
        prompt = GENERATE_SECTIONS_PROMPT.format(
            nb_of_sections=nb_of_sections, module_summary=module_summary
        )
        return json.loads(self.bedrock_generate(prompt))

    def generate_flashcards(self, module_summary):
        prompt = GENERATE_FLASHCARDS_PROMPT.format(module_summary=module_summary)
        return json.loads(self.bedrock_generate(prompt))

    def generate_questions(self, module_summary):
        prompt = GENERATE_QUESTIONS_PROMPT.format(module_summary=module_summary)
        return json.loads(self.bedrock_generate(prompt))

    def generate_course_structure(self, course_id):
        course = self.get_course_details(course_id)
        print("Generating course structure for:", course.title)

        documents = self.get_course_documents(course_id)
        print("Retrieved documents for course:", len(documents))

        course_text = self.combine_course_content(documents)
        print("Combined course content:", course_text)

        modules_data = self.generate_modules(course, course_text)
        print("Generated modules data:", modules_data)

        results = []

        for module_data in modules_data:
            module_entity = Modules(title=module_data["title"], course_id=course_id)
            db.session.add(module_entity)
            db.session.flush()

            sections_data = self.generate_sections(
                module_data["summary"], course.nb_of_sections
            )
            section_results = []

            for section in sections_data:
                section_entity = Sections(
                    title=section["title"],
                    module_id=module_entity.id,
                    is_complete=False,
                )
                db.session.add(section_entity)
                db.session.flush()

                questions_data = self.generate_questions(section["summary"])
                for q in questions_data:
                    question_entity = Questions(
                        section_id=section_entity.id,
                        question_text=q["question"],
                        option1=q["options"][0],
                        option2=q["options"][1],
                        option3=q["options"][2],
                        correct_answer=q["correct_answer"],
                        explanation=q["explanation"],
                    )
                    db.session.add(question_entity)

                section_results.append(
                    {
                        "title": section["title"],
                        "summary": section["summary"],
                        "questions": questions_data,
                    }
                )

            flashcards_data = self.generate_flashcards(module_data["summary"])
            flashcard_entity = FlashCards(
                module_id=module_entity.id,
                question_1=flashcards_data[0]["front"],
                answer_1=flashcards_data[0]["back"],
                question_2=flashcards_data[1]["front"],
                answer_2=flashcards_data[1]["back"],
                question_3=flashcards_data[2]["front"],
                answer_3=flashcards_data[2]["back"],
            )
            db.session.add(flashcard_entity)

            results.append(
                {
                    "module": module_data["title"],
                    "sections": section_results,
                    "flashcards": flashcards_data,
                }
            )

        db.session.commit()
        return results
