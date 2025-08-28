import json
from extensions import db, get_logger
from modules.shared.services.bedrock import BedrockService
from modules.shared.services.translation import TranslationService
from modules.document.entity import Modules, Sections, Paragraphs, Questions
from modules.question.prompts import GENERATE_QUESTIONS_PROMPT


class QuestionService:
    def __init__(self):
        self.bedrock = BedrockService()
        self.translation_service = TranslationService()
        self.logger = get_logger()

    def _translate_and_assign(self, text):
        if not text:
            return {"en": None, "fr": None, "ar": None}
        en, fr, ar = self.translation_service.translate_to_all_languages(text)
        return {"en": en, "fr": fr, "ar": ar}

    def _get_course_paragraphs(self, course_id):
        paragraphs = (
            Paragraphs.query.join(Sections, Sections.id == Paragraphs.section_id)
            .join(Modules, Modules.id == Sections.module_id)
            .filter(Modules.course_id == course_id)
            .all()
        )

        self.logger.info(f"Fetched {len(paragraphs)} paragraphs for course {course_id}")

        if not paragraphs:
            self.logger.warning(f"No paragraphs found for course {course_id}")
            return ""

        combined_text = "\n".join(
            [p.content_body_en for p in paragraphs if p.content_body_en]
        )
        return combined_text

    # Bedrock Call Wrapper
    def _bedrock_generate(self, prompt, max_tokens=10000, temperature=0.5):
        self.logger.info(f"Calling Bedrock with prompt: {prompt}")
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

    # Generator
    def _call_bedrock_for_questions(self, content):
        prompt = GENERATE_QUESTIONS_PROMPT.format(module_summary=content)
        questions_data = self._bedrock_generate(prompt)
        if not isinstance(questions_data, list) or len(questions_data) == 0:
            self.logger.error("Bedrock did not return valid questions")
            return []
        return questions_data

    # Saving Questions to DB
    def _save_questions_to_db(self, course_id, questions_data):
        self.logger.info(
            f"Saving {len(questions_data)} questions for course id {course_id}"
        )
        saved_questions = []

        lang_dettected = False
        lang = ""

        for q in questions_data:
            try:
                # Translate question, explanation, options, and correct answer
                # if not lang_detected
                #   question_texts = self._translate_and_assign(q.get("question"))
                #   explanation_texts = self._translate_and_assign(q.get("explanation"))
                #   lang
                #
                question_texts = self._translate_and_assign(q.get("question"))
                explanation_texts = self._translate_and_assign(q.get("explanation"))
                options = q.get("options", [None, None, None])
                option1_texts = self._translate_and_assign(options[0])
                option2_texts = self._translate_and_assign(options[1])
                option3_texts = self._translate_and_assign(options[2])
                correct_answer_texts = self._translate_and_assign(
                    q.get("correct_answer")
                )

                question_entity = Questions(
                    course_id=course_id,
                    question_text_en=question_texts["en"],
                    question_text_fr=question_texts["fr"],
                    question_text_ar=question_texts["ar"],
                    option1_en=option1_texts["en"],
                    option1_fr=option1_texts["fr"],
                    option1_ar=option1_texts["ar"],
                    option2_en=option2_texts["en"],
                    option2_fr=option2_texts["fr"],
                    option2_ar=option2_texts["ar"],
                    option3_en=option3_texts["en"],
                    option3_fr=option3_texts["fr"],
                    option3_ar=option3_texts["ar"],
                    correct_answer_en=correct_answer_texts["en"],
                    correct_answer_fr=correct_answer_texts["fr"],
                    correct_answer_ar=correct_answer_texts["ar"],
                    explanation_en=explanation_texts["en"],
                    explanation_fr=explanation_texts["fr"],
                    explanation_ar=explanation_texts["ar"],
                )

                db.session.add(question_entity)
                db.session.flush()

                saved_questions.append(
                    {
                        "id": question_entity.id,
                        "question": question_texts,
                        "options": {
                            "en": [
                                option1_texts["en"],
                                option2_texts["en"],
                                option3_texts["en"],
                            ],
                        },
                        "correct_answer": correct_answer_texts,
                        "explanation": explanation_texts,
                    }
                )
            except Exception as e:
                self.logger.error(f"Error saving question for section {course_id}: {e}")

        db.session.commit()
        return saved_questions

    # Main Quiz Generation
    def generate_question(self, course_id):
        # Combine content
        combined_text = self._get_course_paragraphs(course_id)
        if not combined_text:
            return []

        # Generate questions via Bedrock
        questions_data = self._call_bedrock_for_questions(combined_text)
        if not questions_data:
            return []

        # Save and return
        return self._save_questions_to_db(course_id, questions_data)
