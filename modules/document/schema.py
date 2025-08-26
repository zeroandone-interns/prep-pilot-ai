def validate_request(data):
    if not data:
        return False, "No JSON payload provided"
    if "s3_keys" not in data:
        return False, "Missing required field: folder_name"
    return True, None
