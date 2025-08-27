GENERATE_MODULES_PROMPT = """
The course is titled '{title}' and has the following description: {description}.
The intended difficulty level is '{level}', and the expected duration is '{duration}'.
Based on the content below, split it into exactly {nb_of_modules} high-level modules.
Each module should contain exactly {nb_of_sections} sections.
Each section should contain 4 or 5 paragraphs.

Requirements:
1. Modules should progress in difficulty from beginner → advanced, while respecting the target level '{level}'.
2. The overall scope of the course should be achievable within the expected duration '{duration}'.
3. Each module must have a concise title (max 5 words).
4. Each section must have a concise title (max 5 words).
5. Each paragraph must have:
   - "content_title"
   - "content_body"
6. Ensure exactly {nb_of_modules} modules, {nb_of_sections} sections per module, and 4 to 5 paragraphs per section.
7. Paragraphs for each section must be very detailed and cover everything necessary to fully understand the topic.
8. The structure must be strictly hierarchical (Modules → Sections).
9. Avoid redundancy between sections or modules.
10. Respond only in valid JSON. Do not include text outside the JSON array.

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
