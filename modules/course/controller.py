from flask import request, jsonify
from modules.course.services import CourseGenerationService
from modules.flashcard.service import FlashcardService

service = CourseGenerationService()
flashcard_service = FlashcardService()


def course_content_controller():
    data = request.get_json()

    if not data or "course_id" not in data:
        return jsonify({"error": "Missing course_id"}), 400

    course_id = data["course_id"]

    try:
        result = service.generate_course_structure(course_id)
        flashcard_service.generate_flashcard(course_id)

        return jsonify({"status": "success", "course_id": course_id, "details": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def quiz_controller():
    data = request.get_json()

    if not data or "section_id" not in data:
        return jsonify({"error": "Missing section_id"}), 400

    section_id = data["section_id"]

    try:
        result = service.generate_quiz(section_id)
        return jsonify(
            {"status": "success", "section_id": section_id, "details": result}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
