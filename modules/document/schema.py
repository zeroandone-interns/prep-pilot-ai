def validate_request(data):
    if not data:
        return False, "No JSON payload provided"
    if "course_id" not in data or "documents" not in data:
        return False, "Missing required fields: course_id, documents"
    if not isinstance(data["documents"], list):
        return False, "'documents' must be a list"
    return True, None
