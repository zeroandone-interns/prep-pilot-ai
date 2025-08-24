FLASHCARD_PROMPT = """
<instructions>
You are creating flashcards from AWS certification educational content. Generate a JSON array of flashcards based on the provided context.

Each flashcard must follow this exact structure:
{{
  "difficulty": "beginner" | "intermediate" | "advanced",
  "question": "Question text here?",
  "answer": "Complete answer here"
}}

- Create 5-10 flashcards covering key concepts from the context
- Distribute difficulty levels appropriately
- Focus on definitions, comparisons, and technical facts
- Make all answers accurate and complete

Your response must be valid JSON that can be parsed directly. Start with '[' and end with ']'.
</instructions>

<context>
{context}
</context>

<output_format>
[
  {{
    "difficulty": "beginner",
    "question": "What is Amazon S3?",
    "answer": "Amazon S3 (Simple Storage Service) is an object storage service offering industry-leading scalability, data availability, security, and performance."
  }},
  {{
    "difficulty": "intermediate",
    "question": "Example question 2?",
    "answer": "Example answer 2"
  }}
]
</output_format>
"""