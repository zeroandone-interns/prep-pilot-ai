import json
from extensions import get_logger
from modules.document.entity import DocumentChunks, Documents, FlashCards, Modules
from modules.flashcard.prompts import FLASHCARD_PROMPT
from modules.shared.services.bedrock import BedrockService
from extensions import db
import numpy as np

class FlashcardService:
    def __init__(self):
        self.logger = get_logger('[FlashcardService]')
        self.bedrock_service = BedrockService()

    def generate_flashcard(self, course_id):
        self.logger.info("\nGenerating Flashcard...")

        self.logger.debug("\nRetrieving relevant chunks...")
        
        course_chunks = self._retrieve_course_chunks(course_id=course_id)
        
        self.logger.debug(f"\nRetrieved Chunks:\n{len(course_chunks)}")
        self.logger.debug(f"\nRetrieved Chunks:\n{course_chunks[:2]}")

        analyzed_chunks = self._analyze_retrieved_chunks(course_chunks)
        self.logger.debug(f"\nNumber of analyzed chunks ready for flashcard generation: {len(analyzed_chunks)}")
        
        bedrock_response = self._call_bedrock(analyzed_chunks)
        # self.logger.debug(f"\nBedrock responses:\n{bedrock_response}")

        self.save_flashcards_in_db(bedrock_response, course_id)

        return bedrock_response



    def _retrieve_course_chunks(self, course_id):
        self.logger.info(f"\nRetrieving relevant chunks for course_id: {course_id}")
        
        self.logger.info(f"\nFetching documents for course_id: {course_id}")
        documents = Documents.query.filter_by(course_id=course_id).all()
        
        modules = Modules.query.filter_by(course_id=course_id).all()
        module_titles = {module.id: module.title for module in modules}
        
        enhanced_chunks = []
        self.logger.info(f"Aggregating chunks for documents with metadata")
        
        for doc in documents:
            chunks = DocumentChunks.query.filter_by(document_id=doc.id).all()
            
            for chunk in chunks:
                enhanced_chunk = {
                    "id": chunk.id,
                    "tokens": chunk.tokens,
                    "text": chunk.text_en,
                    "embedding": chunk.embeddings_en,
                    "document_id": doc.id,
                    "file_type": doc.type,
                    "course_id": course_id,
                    "module_mapping": self._map_chunk_to_module(chunk.text_en, module_titles)
                }
                
                enhanced_chunks.append(enhanced_chunk)

        self.logger.debug(f"\nRetrieved {len(enhanced_chunks)} enhanced chunks with metadata")
        return enhanced_chunks
        
    def _map_chunk_to_module(self, chunk_text, module_titles):
        relevant_modules = []
        chunk_text_lower = chunk_text.lower()
        
        for module_id, title in module_titles.items():
            #TODO:Implement vector embeddings
            keywords = title.lower().split()
            if any(keyword in chunk_text_lower for keyword in keywords if len(keyword) > 3):
                relevant_modules.append(module_id)
        
        return relevant_modules
        
    def _analyze_retrieved_chunks(self, chunks):
        self.logger.info(f"\nAnalyzing {len(chunks)} retrieved chunks for flashcard generation...")
        
        if not chunks:
            self.logger.warning("No chunks to analyze")
            return []
            
        self.logger.info(f"\nScoring chunks for flashcard suitability...")
        scored_chunks = self._score_chunks_for_flashcards(chunks)
        
        self.logger.info("\nGrouping semantically similar chunks using vector embeddings...")
        semantic_groups = self._group_similar_chunks(scored_chunks)
        
        self.logger.info("\nSelecting representative chunks from each semantic group...")
        selected_chunks = self._select_representative_chunks(semantic_groups)
        
        self.logger.info("Balancing module coverage in selected chunks...")
        balanced_chunks = self._balance_module_coverage(selected_chunks)
        
        self.logger.info(f"\nAnalysis complete. Selected {len(balanced_chunks)} high-quality chunks for flashcards")
        return balanced_chunks
        
    def _score_chunks_for_flashcards(self, chunks):
        #TODO: Make terms dynamic
        terms = [
            "ec2", "s3", "lambda", "dynamodb", "rds", "vpc", "iam", "sns", "sqs", "cloudformation",
            "security", "identity", "availability", "durability", "scalability", "elasticity"
        ]
        
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

            #TODO: Implement file type scoring
            file_type = chunk.get("file_type", "").lower()
            if file_type == "pdf":
                score += 0.5 
            elif file_type in ["ppt", "pptx"]:
                score += 1.0

            chunk["flashcard_score"] = round(score, 2)
            scored_chunks.append(chunk)
        
        # Sort by score in descending order
        scored_chunks.sort(key=lambda x: x.get("flashcard_score", 0), reverse=True)
        self.logger.info("\nChunk scoring complete")
        return scored_chunks
        
    def _group_similar_chunks(self, chunks, similarity_threshold=0.8):
        if not chunks:
            return []
            
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
        
        groups = []
        ungrouped = [c for c in chunks if c.get("embedding") is not None] 

        if not ungrouped:
            self.logger.warning("No embeddings available, returning chunks as singleton groups")
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
        
        self.logger.info(f"\nCreated {len(groups)} semantic groups from {len(chunks)} chunks using vector similarity")
        return groups
        
    def _select_representative_chunks(self, chunk_groups):
        representatives = []
        
        for group in chunk_groups:
            if not group:
                continue
            
            best_chunk = max(group, key=lambda x: x.get("flashcard_score", 0))
            representatives.append(best_chunk)
        return representatives
        
    def _balance_module_coverage(self, chunks, max_chunks=50):
        module_chunks = {}
        for chunk in chunks:
            module_ids = chunk.get("module_mapping", [])
            if not module_ids:
                module_chunks.setdefault("unclassified", []).append(chunk)
                continue
                
            for module_id in module_ids:
                module_chunks.setdefault(module_id, []).append(chunk)
        
        num_modules = len(module_chunks)
        if num_modules == 0:
            return chunks[:max_chunks]
            
        #TODO: Fix duplicate Chunks
        balanced_selection = []
        
        # First pass: get highest-scored chunk from each module
        for module_id, module_chunk_list in module_chunks.items():
            if module_chunk_list:
                best_chunk = max(module_chunk_list, key=lambda x: x.get("flashcard_score", 0))
                balanced_selection.append(best_chunk)
                module_chunks[module_id].remove(best_chunk)
        
        remaining_slots = max_chunks - len(balanced_selection)
        remaining_chunks = [c for sublist in module_chunks.values() for c in sublist]
        remaining_chunks.sort(key=lambda x: x.get("flashcard_score", 0), reverse=True)

        balanced_selection.extend(remaining_chunks[:remaining_slots])
        
        self.logger.info(f"Selected {len(balanced_selection)} chunks with balanced module coverage")
        self.logger.info(f"\n=========================\n{balanced_selection}\n=========================")
        return balanced_selection

    def _call_bedrock(self, chunks):
        self.logger.info("Calling BedrockService for flashcard generation...")
        
        text_chunks = "\n".join(chunk["text"] for chunk in chunks)
        prompt = FLASHCARD_PROMPT.format(context=text_chunks)
        response = self.bedrock_service.invoke_model_with_text(prompt, temperature=0.5, max_tokens=4608)
        return json.loads(response)

    def save_flashcards_in_db(self, flashcards, course_id):
        self.logger.debug("Saving flashcards to database...")
        for card in flashcards:
            self.logger.debug(f"Saving flashcard: \n{card}")
            new_flashcard = FlashCards(
                difficulty=card.get("difficulty"),
                question_1=card.get("question"),
                answer_1=card.get("answer"),
                course_id=course_id,
            )
            db.session.add(new_flashcard)
        db.session.commit()
        self.logger.debug("\nFlashcards saved successfully.")