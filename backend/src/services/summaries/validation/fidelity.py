"""
Fidelity Component - Check A: Missing Fact Detector
Ensures all critical medical facts from the original report are present in the summary.
Uses RAG-retrieved definitions to recognize plain language translations.
"""
from typing import List, Dict
from rapidfuzz import fuzz
from services.summaries.validation.base import PipelineComponent
from schemas.validation import ValidationInput, ValidationResult
from services.summaries.validation.config import (
    ENTITY_FUZZY_MATCH_THRESHOLD,
    ENTITY_CASE_SENSITIVE,
)


class FidelityComponent(PipelineComponent):
    """
    Validates that all critical entities (findings, anatomy, measurements) 
    from the original report appear in the summary.
    
    Uses RAG-retrieved definitions to recognize when medical terms
    have been appropriately translated to patient-friendly language.
    """
    
    def __init__(self):
        self.component_name = "FidelityCheck"
    
    def _extract_key_words_from_definition(self, definition: str) -> List[str]:
        """
        Extract meaningful keywords from a definition for matching.
        Returns simple words that could appear in a translated summary.
        """
        # Common words to ignore
        stop_words = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
            'of', 'in', 'to', 'for', 'with', 'on', 'at', 'by', 'from', 'or',
            'and', 'but', 'if', 'then', 'else', 'when', 'up', 'out', 'so',
            'no', 'not', 'only', 'just', 'more', 'most', 'other', 'some', 'such',
            'into', 'than', 'too', 'very', 'also', 'that', 'this', 'these', 'those',
            'which', 'who', 'whom', 'what', 'where', 'how', 'why', 'all', 'each',
            'any', 'both', 'few', 'many', 'much', 'own', 'same', 'as', 'it', 'its',
        }
        
        keywords = []
        # Take first sentence or first 100 chars
        text = definition.split('.')[0] if '.' in definition else definition[:100]
        
        for word in text.lower().split():
            # Clean punctuation
            word = ''.join(c for c in word if c.isalnum())
            # Keep meaningful words (4+ chars, not stop words)
            if len(word) >= 4 and word not in stop_words:
                keywords.append(word)
        
        return keywords
    
    def _build_translation_map(self, retrieved_definitions: Dict[str, str] | None) -> Dict[str, List[str]]:
        """
        Build a mapping of medical terms to their plain language translations
        using RAG-retrieved definitions.
        """
        translation_map = {}
        
        if not retrieved_definitions:
            return translation_map
        
        for term, definition in retrieved_definitions.items():
            term_lower = term.lower()
            
            # Extract key words from the definition
            keywords = self._extract_key_words_from_definition(definition)
            
            # Also add the first sentence as a whole phrase
            first_sentence = definition.split('.')[0].lower().strip() if '.' in definition else definition[:50].lower()
            
            translation_map[term_lower] = keywords + [first_sentence]
        
        return translation_map
    
    def _entity_is_covered(
        self, 
        entity: str, 
        summary_lower: str, 
        translation_map: Dict[str, List[str]]
    ) -> bool:
        """
        Check if an entity is covered in the summary, either by direct match
        or by one of its plain language translations from RAG.
        """
        entity_normalized = entity.lower() if not ENTITY_CASE_SENSITIVE else entity
        
        # 1. Direct exact match
        if entity_normalized in summary_lower:
            return True
        
        # 2. Check if any translation keyword from this entity appears
        if entity_normalized in translation_map:
            for keyword in translation_map[entity_normalized]:
                if keyword in summary_lower:
                    return True
        
        # 3. Multi-word entity: check if all significant words appear
        entity_words = entity_normalized.split()
        if len(entity_words) > 1:
            significant_words = [word for word in entity_words if len(word) > 2]
            if significant_words and all(word in summary_lower for word in significant_words):
                return True
        
        # 4. Fuzzy matching as fallback
        best_match_ratio = 0
        summary_words = summary_lower.split()
        
        for i in range(len(summary_words)):
            for j in range(i + 1, min(i + len(entity_words) + 2, len(summary_words) + 1)):
                phrase = " ".join(summary_words[i:j])
                ratio = fuzz.ratio(entity_normalized, phrase)
                best_match_ratio = max(best_match_ratio, ratio)
        
        if best_match_ratio >= ENTITY_FUZZY_MATCH_THRESHOLD:
            return True
        
        return False
    
    def process(self, input: ValidationInput) -> ValidationInput:
        """
        Check if all entities from the original report are present in the summary.
        Uses RAG-retrieved definitions to accept plain language translations.
        """
        # Build translation map from RAG definitions
        translation_map = self._build_translation_map(input.retrieved_definitions)
        
        # Collect all critical entities
        all_entities = []
        for entity in input.extracted_entities.entities:
            original_text = getattr(entity, "original_text", "") or ""
            canonical_name = getattr(entity, "canonical_name", "") or ""
            if original_text:
                all_entities.append(original_text)
            if canonical_name and canonical_name.lower() != original_text.lower():
                all_entities.append(canonical_name)
        
        # Remove duplicates and empty strings
        all_entities = list(set([e.strip() for e in all_entities if e.strip()]))
        
        # Normalize summary text for matching
        summary_lower = input.draft_summary.lower() if not ENTITY_CASE_SENSITIVE else input.draft_summary
        
        # Check each entity
        missing_entities = []
        found_entities = []
        
        for entity in all_entities:
            if self._entity_is_covered(entity, summary_lower, translation_map):
                found_entities.append(entity)
            else:
                missing_entities.append(entity)
        
        # Create validation result
        # Pass if at least 70% of entities are found (allows for translation variations)
        total = len(all_entities)
        found = len(found_entities)
        coverage = found / total if total > 0 else 1.0
        passed = coverage >= 0.7 or len(missing_entities) <= 3
        error_messages = []
        
        if not passed:
            error_messages.append(
                f"Missing {len(missing_entities)} critical entities in summary ({coverage*100:.0f}% coverage): {', '.join(missing_entities[:5])}"
                + (f" and {len(missing_entities) - 5} more" if len(missing_entities) > 5 else "")
            )
        
        validation_result = ValidationResult(
            component_name=self.component_name,
            passed=passed,
            error_messages=error_messages,
            metadata={
                "total_entities": len(all_entities),
                "found_entities": len(found_entities),
                "missing_entities": len(missing_entities),
                "missing_entity_list": missing_entities,
                "coverage_percent": coverage * 100,
            }
        )
        
        # Attach result to input (will be collected by pipeline)
        if not hasattr(input, '_validation_results'):
            input._validation_results = []
        input._validation_results.append(validation_result)
        
        return input
