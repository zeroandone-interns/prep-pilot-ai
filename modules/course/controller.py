from flask import request, jsonify
from modules.course.services import CourseContentService


def generate_course_content():
    data = request.get_json()

    if not data or "course_id" not in data:
        return jsonify({"error": "Missing course_id"}), 400

    course_id = data["course_id"]

    service = CourseContentService()

    try:
        result = service.generate_course_structure(course_id)
        return jsonify({"status": "success", "course_id": course_id, "details": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
