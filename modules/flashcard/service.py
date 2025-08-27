import json
from extensions import get_logger
from modules.document.entity import Courses, DocumentChunks, Documents, FlashCards, Modules
from modules.document.services import DocumentProcessingService
from modules.flashcard.prompts import FLASHCARD_PROMPT
from modules.shared.services.bedrock import BedrockService
from extensions import db
import numpy as np

from modules.shared.services.translation import TranslationService

def cosine_similarity(vec1, vec2):          
    if vec1 is None or vec2 is None:
        return 0.0
    
    if not isinstance(vec1, np.ndarray):
        vec1 = np.array(vec1)
    if not isinstance(vec2, np.ndarray):
        vec2 = np.array(vec2)
        
    dot_product = np.dot(vec1, vec2)
    norm_a = np.linalg.norm(vec1)
    norm_b = np.linalg.norm(vec2)
    
    if norm_a == 0 or norm_b == 0:
        return 0
    
    return dot_product / (norm_a * norm_b)

class FlashcardService:
    def __init__(self):
        self.logger = get_logger('[FlashcardService]')
        self.bedrock_service = BedrockService()
        self.document_service = DocumentProcessingService()
        self.translation_service = TranslationService()

    def generate_flashcard(self, course_id, lang):
        self.logger.info("[generate_flashcard] Generating Flashcard...")

        # Get course info to determine the topic
        course = Courses.query.get(course_id)
        if course:
            topic = course.title if course.title else " "
            self.logger.debug(f"[generate_flashcard] Using topic: {topic}")

        self.logger.debug(f"[generate_flashcard] Retrieving relevant chunks...")
        course_chunks = self._retrieve_course_chunks(course_id=course_id, lang=lang)

        self.logger.debug(f"[generate_flashcard] Retrieved Chunks:\n{len(course_chunks)}")
        self.logger.debug(f"[generate_flashcard] Retrieved Chunks:\n{course_chunks[:2]}")

        analyzed_chunks = self._analyze_retrieved_chunks(course_chunks, course_id)
        self.logger.debug(f"[generate_flashcard] Number of analyzed chunks ready for flashcard generation: {len(analyzed_chunks)}")

        self.logger.info(f"[generate_flashcard] Calling BedrockService for flashcard generation on topic: {topic}")
        bedrock_response = self._call_bedrock(analyzed_chunks, topic=topic)
        # self.logger.debug(f"\nBedrock responses:\n{bedrock_response}")

        self.save_flashcards_in_db(bedrock_response, course_id)
        self.logger.debug("\nFlashcards saved successfully.")

        return bedrock_response

    def _retrieve_course_chunks(self, course_id, lang):
        self.logger.info(f"[_retrieve_course_chunks] Retrieving relevant chunks for course_id: {course_id}")

        self.logger.info(f"[_retrieve_course_chunks] Fetching documents for course_id: {course_id}")
        documents = Documents.query.filter_by(course_id=course_id).all()
        
        modules = Modules.query.filter_by(course_id=course_id).all()
        module_titles = {module.id: module.title_en for module in modules}
        
        enhanced_chunks = []
        self.logger.info(f"[_retrieve_course_chunks] Aggregating chunks for documents with metadata")

        for doc in documents:
            chunks = DocumentChunks.query.filter_by(document_id=doc.id).all()

            for chunk in chunks:
                text = {
                    "en": chunk.text_en,
                    "ar": chunk.text_ar,
                    "fr": chunk.text_fr
                }[lang]
                
                embeddings = {
                    "en": chunk.embeddings_en,
                    "ar": chunk.embeddings_ar,
                    "fr": chunk.embeddings_fr
                }[lang]
                
                enhanced_chunk = {
                    "id": chunk.id,
                    "tokens": chunk.tokens,
                    "text": text,
                    "embedding": embeddings,
                    "document_id": doc.id,
                    "module_mapping": self._map_chunk_to_module(text, embeddings, module_titles)
                }
                
                enhanced_chunks.append(enhanced_chunk)

        self.logger.info(f"[_retrieve_course_chunks] Retrieved {len(enhanced_chunks)} enhanced chunks with metadata")
        return enhanced_chunks


    def _map_chunk_to_module(self, chunk_text, chunk_embedding, module_titles):
        self.logger.debug(f"Chunk text: {chunk_text}")
        self.logger.debug(f"Chunk Embedding: {chunk_embedding}")
        title_embeddings = {}
        for module_id, title in module_titles.items():
            title_embeddings[module_id] = self.bedrock_service.generate_embedding(title)

        relevant_modules = []
        for module_id, title in module_titles.items():
            title_embedding = title_embeddings[module_id]
            similartiy_score = cosine_similarity(title_embedding, chunk_embedding)
            if similartiy_score > 0.5:
                relevant_modules.append(module_id)
        
        return relevant_modules
        
    def _analyze_retrieved_chunks(self, chunks, course_id):
        self.logger.info(f"[_analyze_retrieved_chunks] Analyzing {len(chunks)} retrieved chunks for flashcard generation...")
        
        if not chunks:
            self.logger.warning("[_analyze_retrieved_chunks] No chunks to analyze")
            return []

        terms = Courses.query.filter_by(id=course_id).first().terms or []
        self.logger.info(f"[_analyze_retrieved_chunks] Key terms for course_id {course_id}: {terms}")

        self.logger.info(f"[_analyze_retrieved_chunks] Scoring chunks for flashcard suitability...")
        scored_chunks = self._score_chunks_for_flashcards(chunks, terms)

        self.logger.info(f"[_analyze_retrieved_chunks] Grouping semantically similar chunks using vector embeddings...")
        semantic_groups = self._group_similar_chunks(scored_chunks)
        self.logger.info(f"[_analyze_retrieved_chunks] Groups ========================={semantic_groups} =========================")

        self.logger.info(f"[_analyze_retrieved_chunks] Selecting representative chunks from each semantic group...")
        selected_chunks = self._select_representative_chunks(semantic_groups)

        self.logger.info(f"[_analyze_retrieved_chunks] Balancing module coverage in selected chunks...")
        balanced_chunks = self._balance_module_coverage(selected_chunks)
        self.logger.info(f"[_analyze_retrieved_chunks] Analysis complete. Selected {len(balanced_chunks)} high-quality chunks for flashcards")
        self.logger.debug(f"[_analyze_retrieved_chunks] =========================\n{balanced_chunks}\n=========================")

        return balanced_chunks
        
    def _score_chunks_for_flashcards(self, chunks, terms):
        terms = terms
        
        definition_patterns = [
            "is a", "refers to", "is defined as", "is the", "means", "represents", 
            "consists of", "comprises", "allows", "enables"
        ]
        
        comparison_patterns = [
            "versus", "compared to", "difference between", "advantages of", 
            "benefits of", "in contrast to", "unlike"
        ]
        
        list_patterns = [":", "• ", "- ", "1.", "2.", "first", "second", "key", "important"]
        
        scored_chunks = []
        
        for chunk in chunks:
            score = 0
            text = chunk["text"].lower()
            
            token_count = chunk.get("tokens", 0)
            if 50 <= token_count <= 150:
                score += 1
                
            term_count = sum(1 for term in terms if term in text)
            score += min(term_count * 0.5, 3)
            
            def_count = sum(1 for pattern in definition_patterns if pattern in text)
            score += min(def_count * 1.0, 3) 
            
            comp_count = sum(1 for pattern in comparison_patterns if pattern in text)
            score += min(comp_count * 1.5, 3)

            list_count = sum(1 for pattern in list_patterns if pattern in text)
            score += min(list_count * 0.5, 2)
            
            if chunk.get("module_mapping"):
                score += min(len(chunk.get("module_mapping")) * 0.5, 1.5)

            chunk["flashcard_score"] = round(score, 2)
            scored_chunks.append(chunk)
        
        # Sort by score in descending order
        scored_chunks.sort(key=lambda x: x.get("flashcard_score", 0), reverse=True)
        self.logger.info("[_score_chunks_for_flashcards] Chunk scoring complete")
        return scored_chunks
        
    def _group_similar_chunks(self, chunks):
        if not chunks:
            return []

        similarity_threshold = 0.8
        groups = []
        ungrouped = [c for c in chunks if c.get("embedding") is not None] 

        if not ungrouped:
            self.logger.warning("[_group_similar_chunks] No embeddings available, returning chunks as singleton groups")
            return [[c] for c in chunks]
            
        while ungrouped:
            current = ungrouped.pop(0)
            current_group = [current]
            
            i = 0
            while i < len(ungrouped):
                chunk = ungrouped[i]
                
                similarity = cosine_similarity(current["embedding"], chunk["embedding"])
                
                if similarity >= similarity_threshold:
                    current_group.append(chunk)
                    ungrouped.pop(i)
                else:
                    i += 1
            
            groups.append(current_group)

        self.logger.info(f"[_group_similar_chunks] Created {len(groups)} semantic groups from {len(chunks)} chunks using vector similarity")
        return groups
        
    def _select_representative_chunks(self, chunk_groups):
        representatives = []
        
        for group in chunk_groups:
            if not group:
                continue
            
            sorted_chunks = sorted(group, key=lambda x: x.get("flashcard_score", 0), reverse=True)
            top_chunks = sorted_chunks[:min(3, len(sorted_chunks))]
            representatives.extend(top_chunks)
            
        return representatives
    
    def _balance_module_coverage(self, chunks):
        module_chunks = {}
        
        max_chunks = self.document_service.context_window // self.document_service.chunk_size
        self.logger.info(f"[_balance_module_coverage] Max chunks for context window: {max_chunks}")
        
        # Group chunks by their module IDs
        for chunk in chunks:
            module_ids = chunk.get("module_mapping", [])
            if not module_ids:
                module_chunks.setdefault("unclassified", []).append(chunk)
                continue
                
            for module_id in module_ids:
                module_chunks.setdefault(module_id, []).append(chunk)
        
        num_modules = len(module_chunks)
        if num_modules == 0:
            return {"unclassified": chunks[:max_chunks]}
        
        # Calculate how many chunks to take from each module
        chunks_per_module = max(1, max_chunks // num_modules)
        self.logger.info(f"[_balance_module_coverage] Selecting exactly {chunks_per_module} chunks per module from {num_modules} modules")

        # Create a structured output preserving module relationships
        balanced_selection_by_module = {}
        
        # One simple loop: just take top N chunks from each module
        for module_id, module_chunk_list in module_chunks.items():
            if not module_chunk_list:
                continue
                
            # Sort chunks within this module by score
            sorted_chunks = sorted(module_chunk_list, key=lambda x: x.get("flashcard_score", 0), reverse=True)
            
            # Select top chunks_per_module chunks from this module
            selected_chunks = sorted_chunks[:chunks_per_module]
            balanced_selection_by_module[module_id] = selected_chunks
        
        self.logger.info(f"[_balance_module_coverage] Selected chunks across {len(balanced_selection_by_module)} modules")
        
        return balanced_selection_by_module


    def _call_bedrock(self, module_chunks, topic):
        # Format context with module structure preserved
        context_parts = []
        
        # Format context by module ID
        for module_id, chunks in module_chunks.items():
            if not chunks:
                continue
            
            # Add module ID heading (this will be used to structure the response)
            module_section = f"\n--- MODULE ID: {module_id} ---\n\n"
            
            # Add all chunk texts for this module
            module_section += "\n\n".join(chunk["text"] for chunk in chunks)
            context_parts.append(module_section)
        
        # Join all module contexts
        formatted_context = "\n\n".join(context_parts)
        
        # Build the prompt with the formatted context and topic
        prompt = FLASHCARD_PROMPT.format(context=formatted_context, topic=topic)
        
        # Call Bedrock with the structured context
        response = self.bedrock_service.invoke_model_with_text(prompt, temperature=0.5, max_tokens=4608)
        return json.loads(response)

    def save_flashcards_in_db(self, module_flashcards, course_id):
        total_saved = 0
        
        for module_id_str, flashcards in module_flashcards.items():
            if not isinstance(flashcards, list):
                self.logger.warning(f"Expected list of flashcards for module {module_id_str}, got {type(flashcards)}")
                continue
                
            self.logger.info(f"Processing {len(flashcards)} flashcards for module {module_id_str}")
            
            for card in flashcards:
                translated_question = self.translation_service._translate_and_assign(card.get("question"))
                translated_answer = self.translation_service._translate_and_assign(card.get("answer"))
                
                
                new_flashcard = FlashCards(
                    difficulty=card.get("difficulty"),
                    question_en=translated_question.get("en"),
                    question_ar=translated_question.get("ar"),
                    question_fr=translated_question.get("fr"),
                    answer_en=translated_answer.get("en"),
                    answer_ar=translated_answer.get("ar"),
                    answer_fr=translated_answer.get("fr"),
                    module_id=module_id_str if module_id_str != "unclassified" else None
                )
                
                db.session.add(new_flashcard)
                total_saved += 1
            
        db.session.commit()
        self.logger.info(f"Saved {total_saved} flashcards to database for course {course_id}")
        
        

