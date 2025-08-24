import json
from extensions import get_logger
from modules.document.entity import DocumentChunks, Documents, FlashCards, Modules
from modules.flashcard.prompts import FLASHCARD_PROMPT
from modules.shared.services.bedrock import BedrockService
from extensions import db

class FlashcardService:
    def __init__(self):
        self.logger = get_logger()
        self.bedrock_service = BedrockService()

    def generate_flashcard(self, course_id):
        self.logger.info("Generating flashcard...")

        # Retrieve chunks
        self.logger.info("Retrieving relevant chunks...")
        course_chunks = self._retrieve_course_chunks(course_id=course_id)
        self.logger.info(f"Retrieved Chunks:\n{len(course_chunks)}")
        self.logger.info(f"Retrieved Chunks:\n{course_chunks[:2]}")

        
        # Analyze the retrieved chunks
        analyzed_chunks = self._analyze_retrieved_chunks(course_chunks)
        self.logger.info(f"Number of analyzed chunks ready for flashcard generation: {len(analyzed_chunks)}")
        # self.logger.info(f"Analyzed Chunks:\n{json.dumps(analyzed_chunks, indent=4)}")

        # Call BedrockService with analyzed chunks
        bedrock_response = self._call_bedrock(analyzed_chunks)
        self.logger.info(f"Bedrock responses:\n{bedrock_response}")

        self.save_flashcards_in_db(bedrock_response, course_id)

        return bedrock_response



    def _retrieve_course_chunks(self, course_id):
        self.logger.info(f"Retrieving relevant chunks for course_id: {course_id}")
        
        self.logger.info(f"Fetching documents for course_id: {course_id}")
        documents = Documents.query.filter_by(course_id=course_id).all()
        
        # Get module information for content mapping
        modules = Modules.query.filter_by(course_id=course_id).all()
        module_titles = {module.id: module.title for module in modules}
        
        enhanced_chunks = []
        self.logger.info(f"Aggregating chunks for documents with metadata")
        
        for doc in documents:
            # self.logger.info(f"Fetching chunks for document_id: {doc.id}")
            chunks = DocumentChunks.query.filter_by(document_id=doc.id).all()
            
            for chunk in chunks:
                # Enhanced chunk with metadata for better filtering
                enhanced_chunk = {
                    "id": chunk.id,
                    "text": chunk.text_en,  # Using only English text
                    "tokens": chunk.tokens,
                    "embedding": chunk.embeddings_en,  # Using only English embeddings
                    "document_id": doc.id,
                    "file_type": doc.type,  # Document file type/extension
                    "course_id": course_id,
                    "module_mapping": self._map_chunk_to_module(chunk.text_en, module_titles)
                }
                
                enhanced_chunks.append(enhanced_chunk)

        self.logger.info(f"Retrieved {len(enhanced_chunks)} enhanced chunks with metadata")
        return enhanced_chunks
        
    def _map_chunk_to_module(self, chunk_text, module_titles):
        """
        Maps a chunk to relevant modules based on content similarity.
        Uses simple keyword matching between chunk text and module titles.
        
        Args:
            chunk_text (str): The text content of the chunk
            module_titles (dict): Dictionary of module_id: module_title pairs
            
        Returns:
            list: List of module IDs that this chunk likely belongs to
        """
        relevant_modules = []
        chunk_text_lower = chunk_text.lower()
        
        for module_id, title in module_titles.items():
            # Simple keyword matching - can be enhanced with embeddings later
            keywords = title.lower().split()
            if any(keyword in chunk_text_lower for keyword in keywords if len(keyword) > 3):
                relevant_modules.append(module_id)
        
        return relevant_modules
        
    def _analyze_retrieved_chunks(self, chunks):
        """
        Analyze and score chunks for flashcard generation suitability.
        
        This method:
        1. Scores chunks based on educational value
        2. Identifies key concepts and terminology
        3. Groups semantically similar content
        4. Prioritizes high-information-density chunks
        
        Args:
            chunks (list): List of enhanced chunk dictionaries from _retrieve_course_chunks
            
        Returns:
            list: List of prioritized chunks with analysis metadata
        """
        self.logger.info(f"Analyzing {len(chunks)} retrieved chunks for flashcard generation...")
        
        if not chunks:
            self.logger.warning("No chunks to analyze")
            return []
            
        # Step 1: Score each chunk for flashcard suitability
        scored_chunks = self._score_chunks_for_flashcards(chunks)
        
        # Step 2: Group semantically similar chunks to avoid redundancy
        semantic_groups = self._group_similar_chunks(scored_chunks)
        
        # Step 3: Select representative chunks from each group
        selected_chunks = self._select_representative_chunks(semantic_groups)
        
        # Step 4: Balance module coverage
        balanced_chunks = self._balance_module_coverage(selected_chunks)
        
        self.logger.info(f"Analysis complete. Selected {len(balanced_chunks)} high-quality chunks for flashcards")
        return balanced_chunks
        
    def _score_chunks_for_flashcards(self, chunks):
        """
        Score chunks based on their suitability for flashcard generation.
        
        Scoring factors:
        - Presence of key terminology
        - Definitional patterns
        - Information density
        - Educational value
        
        Args:
            chunks (list): Enhanced chunk dictionaries
            
        Returns:
            list: Chunks with added score property
        """
        self.logger.info("Scoring chunks for flashcard suitability...")
        
        # Common AWS service terms and certification concepts
        aws_terms = [
            "ec2", "s3", "lambda", "dynamodb", "rds", "vpc", "iam", "sns", "sqs", "cloudformation",
            "security", "identity", "availability", "durability", "scalability", "elasticity"
        ]
        
        # Pattern indicators of good flashcard content
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
            
            # Base score - longer chunks might contain more useful info, but not too long
            token_count = chunk.get("tokens", 0)
            if 50 <= token_count <= 150:
                score += 1  # Sweet spot for flashcard content length
                
            # Check for AWS terminology
            term_count = sum(1 for term in aws_terms if term in text)
            score += min(term_count * 0.5, 3)  # Cap at 3 points for terms
            
            # Check for definitional patterns
            def_count = sum(1 for pattern in definition_patterns if pattern in text)
            score += min(def_count * 1.0, 3)  # Definitions are valuable for flashcards
            
            # Check for comparison patterns
            comp_count = sum(1 for pattern in comparison_patterns if pattern in text)
            score += min(comp_count * 1.5, 3)  # Comparisons make excellent flashcards
            
            # Check for list patterns that might indicate key points
            list_count = sum(1 for pattern in list_patterns if pattern in text)
            score += min(list_count * 0.5, 2)
            
            # Module mapping - chunks that map to modules are likely more relevant
            if chunk.get("module_mapping"):
                score += min(len(chunk.get("module_mapping")) * 0.5, 1.5)
                
            # File type bonus - certain formats may contain more structured information
            file_type = chunk.get("file_type", "").lower()
            if file_type == "pdf":
                score += 0.5  # PDFs often contain structured, formal content
            elif file_type in ["ppt", "pptx"]:
                score += 1.0  # Presentations typically have key points
            
            # Add score to chunk
            chunk["flashcard_score"] = round(score, 2)
            scored_chunks.append(chunk)
        
        # Sort by score in descending order
        scored_chunks.sort(key=lambda x: x.get("flashcard_score", 0), reverse=True)
        self.logger.info("Chunk scoring complete")
        return scored_chunks
        
    def _group_similar_chunks(self, chunks, similarity_threshold=0.8):
        """
        Group semantically similar chunks to avoid redundant flashcards.
        
        Uses embeddings and vector similarity to find semantic relationships
        between chunks, providing more accurate grouping than keyword matching.
        
        Args:
            chunks (list): Scored chunks
            similarity_threshold (float): Threshold for considering chunks similar (0-1)
            
        Returns:
            list: List of chunk groups (each group is a list of similar chunks)
        """
        self.logger.info("Grouping semantically similar chunks using vector embeddings...")
        
        if not chunks:
            return []
            
        
        # Generate embeddings for each chunk
        # self.logger.info("Generating embeddings for chunks...")
        
        # Process chunks in batches to avoid hitting API limits
        # batch_size = 20  # Adjust based on API limits
        # all_chunks = []
        
        # for i in range(0, len(chunks), batch_size):
        #     batch = chunks[i:i+batch_size]
        #     try:
        #         # Generate embeddings for this batch
        #         for chunk in batch:
        #             # Use existing embedding if available from database or generate new one
        #             if "id" in chunk:
        #                 # Try to fetch from database first to avoid regenerating
        #                 from modules.document.entity import DocumentChunks
        #                 from extensions import db
        #                 from sqlalchemy import text
                        
        #                 db_chunk = db.session.query(DocumentChunks).get(chunk["id"])
        #                 if db_chunk and db_chunk.embeddings_en is not None:
        #                     # Use the existing embedding from database
        #                     chunk["embedding"] = db_chunk.embeddings_en
        #                 else:
        #                     # Generate new embedding
        #                     chunk["embedding"] = self.bedrock_service.generate_embedding_query(chunk["text"])
        #             else:
        #                 # Generate new embedding
        #                 chunk["embedding"] = self.bedrock_service.generate_embedding_query(chunk["text"])
                    
        #             all_chunks.append(chunk)
                    
        #     except Exception as e:
        #         self.logger.error(f"Error generating embeddings: {str(e)}")
        #         # Fall back to non-embedded chunks for this batch
        #         all_chunks.extend(batch)
                
        # Helper function to calculate cosine similarity between two vectors
        def cosine_similarity(vec1, vec2):
            import numpy as np
            
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
        
        # Group chunks based on embedding similarity
        groups = []
        ungrouped = [c for c in chunks if c.get("embedding") is not None]  # Only use chunks with embeddings

        # If we couldn't generate embeddings for chunks, fall back to the chunks as is
        if not ungrouped:
            self.logger.warning("No embeddings available, returning chunks as singleton groups")
            return [[c] for c in chunks]
            
        while ungrouped:
            current = ungrouped.pop(0)
            current_group = [current]
            
            i = 0
            while i < len(ungrouped):
                chunk = ungrouped[i]
                
                # Calculate cosine similarity between chunk embeddings
                similarity = cosine_similarity(current["embedding"], chunk["embedding"])
                
                if similarity >= similarity_threshold:
                    current_group.append(chunk)
                    ungrouped.pop(i)
                else:
                    i += 1
            
            groups.append(current_group)
        
        self.logger.info(f"Created {len(groups)} semantic groups from {len(chunks)} chunks using vector similarity")
        return groups
        
    def _select_representative_chunks(self, chunk_groups):
        """
        Select the best representative chunk from each semantic group.
        
        Args:
            chunk_groups (list): List of chunk groups
            
        Returns:
            list: Selected representative chunks
        """
        self.logger.info("Selecting representative chunks from each semantic group...")
        
        representatives = []
        
        for group in chunk_groups:
            if not group:
                continue
                
            # Select the highest scored chunk in each group
            best_chunk = max(group, key=lambda x: x.get("flashcard_score", 0))
            representatives.append(best_chunk)
        
        return representatives
        
    def _balance_module_coverage(self, chunks, max_chunks=50):
        """
        Ensure balanced coverage across all modules.
        
        Args:
            chunks (list): Representative chunks
            max_chunks (int): Maximum number of chunks to return
            
        Returns:
            list: Balanced selection of chunks
        """
        self.logger.info("Balancing module coverage in selected chunks...")
        
        # Group chunks by module
        module_chunks = {}
        for chunk in chunks:
            module_ids = chunk.get("module_mapping", [])
            if not module_ids:
                # If no module mapping, put in a special category
                module_chunks.setdefault("unclassified", []).append(chunk)
                continue
                
            for module_id in module_ids:
                module_chunks.setdefault(module_id, []).append(chunk)
        
        # Determine how many chunks to take from each module
        num_modules = len(module_chunks)
        if num_modules == 0:
            return chunks[:max_chunks]  # Just return top chunks if no module mapping
            
        # Try to get at least one chunk per module
        balanced_selection = []
        
        # First pass: get highest-scored chunk from each module
        for module_id, module_chunk_list in module_chunks.items():
            if module_chunk_list:
                # Sort by score and take the best chunk
                best_chunk = max(module_chunk_list, key=lambda x: x.get("flashcard_score", 0))
                balanced_selection.append(best_chunk)
                # Remove this chunk from consideration for second pass
                module_chunks[module_id].remove(best_chunk)
        
        # If we need more chunks, take next best chunks from modules with most content
        remaining_slots = max_chunks - len(balanced_selection)
        remaining_chunks = [c for sublist in module_chunks.values() for c in sublist]
        remaining_chunks.sort(key=lambda x: x.get("flashcard_score", 0), reverse=True)
        
        balanced_selection.extend(remaining_chunks[:remaining_slots])
        
        self.logger.info(f"Selected {len(balanced_selection)} chunks with balanced module coverage")
        return balanced_selection

    def _call_bedrock(self, chunks):
        self.logger.info("Calling BedrockService for flashcard generation...")
        # try:
        self.logger.info(f"Grouping chunks for Bedrock prompt...")
        text_chunks = "\n".join(chunk["text"] for chunk in chunks)
        self.logger.info("Configuring Prompt...")
        prompt = FLASHCARD_PROMPT.format(context=text_chunks)
        # self.logger.info(f"Prompt for Bedrock Model:\n{prompt}")
        self.logger.info("Calling Bedrock Model...")
        response = self.bedrock_service.invoke_model_with_text(prompt, temperature=0.5, max_tokens=4608)
        # self.logger.info(f"Bedrock Model Response:\n{response}")
        return json.loads(response)
        # except Exception as e:
        #     self.logger.error(f"Error processing with Bedrock: {str(e)}")
        #     return "Error generating flashcards"

    def save_flashcards_in_db(self, flashcards, course_id):
        self.logger.info("Saving flashcards to database...")
        for card in flashcards:
            self.logger.info(f"Saving flashcard: \n{card}")
            new_flashcard = FlashCards(
                difficulty=card.get("difficulty"),
                question_1=card.get("question"),
                answer_1=card.get("answer"),
                course_id=course_id,
            )
            db.session.add(new_flashcard)
        db.session.commit()
        self.logger.info("Flashcards saved successfully.")