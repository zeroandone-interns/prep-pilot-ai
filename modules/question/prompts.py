GENERATE_QUESTIONS_PROMPT = """
Create exactly 10 multiple-choice questions (MCQs) from the following module: {module_summary}

Each question must have exactly 3 options, 1 correct answer, and an explanation.

Respond only in valid JSON format:
[
  {{
    "question": "Question text",
    "options": ["Option 1", "Option 2", "Option 3"],
    "correct_answer": "Option 2",
    "explanation": "Why this is correct"
  }},
  {{
    "question": "Question text",
    "options": ["Option 1", "Option 2", "Option 3"],
    "correct_answer": "Option 1",
    "explanation": "Why this is correct"
  }},
  {{
    "question": "Question text",
    "options": ["Option 1", "Option 2", "Option 3"],
    "correct_answer": "Option 3",
    "explanation": "Why this is correct"
  }}
]
"""
