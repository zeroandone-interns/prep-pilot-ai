from flask import request, jsonify
from modules.course.services import CourseGenerationService
from modules.flashcard.service import FlashcardService
from modules.question.service import QuestionService

course_service = CourseGenerationService()
flashcard_service = FlashcardService()
question_service = QuestionService()


def course_content_controller():
    data = request.get_json()

    if not data or "course_id" not in data:
        return jsonify({"error": "Missing course_id"}), 400

    course_id = data["course_id"]

    try:
        result = course_service.generate_course_structure(course_id)
        flashcard_service.generate_flashcard(course_id)
        question_service.generate_question(course_id)

        return jsonify({"status": "success", "course_id": course_id, "details": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
