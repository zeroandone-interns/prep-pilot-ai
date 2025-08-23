GENERATE_MODULES_PROMPT = """
The course is titled '{title}' and has the following description: {description}.
Based on the content below, split it into exactly {nb_of_modules} high-level modules.
Each module should contain exactly {nb_of_sections} sections.
Each section should contain 4 or 5 paragraphs.

Requirements:
1. Modules should progress in difficulty from beginner → advanced.
2. Each module must have a concise title (max 5 words).
3. Each section must have a concise title (max 5 words).
4. Each paragraph must have:
   - "content_title"
   - "content_body"
5. Ensure exactly {nb_of_modules} modules, {nb_of_sections} sections per module, and 4 to 5 paragraphs per section.
6. Paragraphs for each section must be very detailed and cover everything necessary to fully understand the topic.
7. The structure must be strictly hierarchical (Modules → Sections).
8. Avoid redundancy between sections or modules.
9. Respond only in valid JSON. Do not include text outside the JSON array.

Content:
{content}

Example JSON format:
[
  {{
    "title": "Module 1 Title",
    "sections": [
      {{
        "title": "Section 1 Title",
        "paragraphs": [
          {{"content_title": "Paragraph 1 Title", "content_body": "Paragraph 1 Body"}},
          {{"content_title": "Paragraph 2 Title", "content_body": "Paragraph 2 Body"}},
          {{"content_title": "Paragraph 3 Title", "content_body": "Paragraph 3 Body"}},
          {{"content_title": "Paragraph 4 Title", "content_body": "Paragraph 4 Body"}},
          {{"content_title": "Paragraph 5 Title", "content_body": "Paragraph 5 Body"}}
        ]
      }}
    ]
  }}
]
"""


GENERATE_QUESTIONS_PROMPT = """
Create exactly 3 multiple-choice questions (MCQs) from the following module: {module_summary}

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
