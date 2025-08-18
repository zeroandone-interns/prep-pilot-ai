def validate_request(data):
    if not data:
        return False, "No JSON payload provided"
    if "folder_name" not in data:
        return False, "Missing required field: folder_name"
    return True, None
