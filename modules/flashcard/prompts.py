FLASHCARD_PROMPT = """
<instructions>
You are creating flashcards from {topic} educational content. Generate a structured JSON object with module IDs as keys and arrays of flashcards as values.

The response should follow this exact structure:
{{
  "moduleId1": [
    {{
      "difficulty": "beginner" | "intermediate" | "advanced",
      "question": "Question text here?",
      "answer": "Complete answer here"
    }},
    ...more flashcards for this module
  ],
  "moduleId2": [
    {{
      "difficulty": "intermediate",
      "question": "Another question?",
      "answer": "Another answer"
    }},
    ...more flashcards for this module
  ]
}}

Important notes:
- Create 2-3 flashcards for each module section in the context
- Distribute difficulty levels appropriately
- Focus on definitions, comparisons, and technical facts
- Make all answers accurate and complete
- Pay attention to module IDs in the context marked with "--- MODULE ID: [id] ---"
- Group flashcards by their respective module IDs
- For content from the "unclassified" section, discard them

Your response must be valid JSON that can be parsed directly.
</instructions>

<context>
{context}
</context>

<output_format>
{{
  "m1": [
    {{
      "difficulty": "beginner",
      "question": "What is this concept?",
      "answer": "This is the explanation of the concept, covering its key attributes and importance."
    }},
    {{
      "difficulty": "intermediate",
      "question": "What is the difference between concept A and concept B?",
      "answer": "Concept A differs from concept B in these specific ways... while they share these commonalities..."
    }}
  ],
  "m2": [
    {{
      "difficulty": "advanced",
      "question": "How does this technology solve a specific problem?",
      "answer": "This technology addresses the problem by implementing these mechanisms and providing these benefits..."
    }}
  ]
}}
</output_format>
"""