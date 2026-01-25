"""
RAG (Retrieval-Augmented Generation) Service for medical term definitions.

This service retrieves trusted, standardized definitions for medical terms
using a multi-source approach:
1. UMLS (Unified Medical Language System) - Authoritative medical definitions
   (Reuses SpacyExtractor from entity_extraction to avoid duplication)
2. PLABA/Cochrane datasets - Plain language translations

Provides a "Definitions Context" for the summarization pipeline.
"""
import logging
import re
from typing import Dict, List, Optional
from schemas.validation import EntityExtractionResult
from services.summaries.glossary_builder import GlossaryBuilder
from services.summaries.entity_extraction.spacy import SpacyExtractor

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG service that retrieves medical term definitions from trusted sources.
    
    Uses a hybrid approach:
    1. UMLS (primary) - Authoritative medical definitions via SpacyExtractor (reuses existing component)
    2. PLABA/Cochrane datasets (fallback) - Plain language translations
    
    Trigger: Takes the list of medical terms from Step 1 (Entity Extraction)
    Action: Searches UMLS (via SpacyExtractor) and trusted medical glossary
    Output: A "Definitions Context" dictionary to feed into the next step
    """
    
    def __init__(
        self,
        dataset_path: Optional[str] = None,
        preferred_sources: Optional[List[str]] = None,
        use_umls: bool = True,
        umls_min_confidence: float = 0.7
    ):
        """
        Initialize the RAG service.
        
        Args:
            dataset_path: Path to the merged_plain_language_dataset.csv file
            preferred_sources: Preferred source datasets (default: ['PLABA', 'Cochrane'])
            use_umls: Whether to use UMLS retrieval (default: True)
            umls_min_confidence: Minimum confidence for UMLS matches (0-1)
        """
        if preferred_sources is None:
            preferred_sources = ['PLABA', 'Cochrane']
        
        self.preferred_sources = preferred_sources
        self.use_umls = use_umls
        self.umls_min_confidence = umls_min_confidence
        
        # Reuse SpacyExtractor from entity_extraction (avoids duplication)
        if self.use_umls:
            try:
                self.spacy_component = SpacyExtractor()
                logger.info("UMLS retriever initialized (using SpacyExtractor)")
            except Exception as e:
                logger.warning(f"Could not initialize SpacyExtractor: {str(e)}. Will use dataset only.")
                self.use_umls = False
                self.spacy_component = None
        else:
            self.spacy_component = None
        
        # Initialize dataset glossary builder
        self.glossary_builder = GlossaryBuilder(dataset_path=dataset_path)
        self._glossary_loaded = False
    
    def _ensure_glossary_loaded(self):
        """Ensure the glossary is loaded."""
        if not self._glossary_loaded:
            self.glossary_builder.build_glossary(preferred_sources=self.preferred_sources)
            self._glossary_loaded = True
    
    def _extract_medical_terms(self, text: str) -> List[str]:
        """
        Extract potential medical terms from text.
        
        Args:
            text: Text to extract terms from
        
        Returns:
            List of potential medical terms
        """
        terms = []
        
        # Extract capitalized words/phrases (common medical terms)
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        terms.extend(capitalized)
        
        # Extract abbreviations (all caps, 2-5 chars)
        abbreviations = re.findall(r'\b[A-Z]{2,5}\b', text)
        terms.extend(abbreviations)
        
        # Extract compound terms (e.g., "opacification", "pneumothorax")
        # Words longer than 8 characters are often medical terms
        long_words = re.findall(r'\b[a-zA-Z]{8,}\b', text)
        terms.extend(long_words)
        
        # Remove duplicates and normalize
        unique_terms = list(set(term.lower().strip() for term in terms if len(term.strip()) > 2))
        
        return unique_terms
    
    def retrieve_definitions(
        self,
        extracted_entities: EntityExtractionResult,
        medical_report: Optional[str] = None,
        max_definitions: int = 20
    ) -> Dict[str, str]:
        """
        Retrieve definitions for medical terms found in the extracted entities.
        
        This is the main RAG pipeline step using hybrid retrieval:
        1. UMLS (primary) - Authoritative medical definitions via SpacyExtractor
        2. PLABA/Cochrane dataset (fallback) - Plain language translations
        
        Args:
            extracted_entities: EntityExtractionResult from Step 1
            medical_report: Optional original medical report for additional context
            max_definitions: Maximum number of definitions to return
        
        Returns:
            Dictionary mapping medical terms to their plain language definitions
        """
        definitions = {}
        
        # Collect all potential terms from entities
        all_terms = []
        for entity in extracted_entities.entities:
            original_text = getattr(entity, "original_text", "") or ""
            canonical_name = getattr(entity, "canonical_name", "") or ""
            if original_text:
                all_terms.append(original_text)
            if canonical_name and canonical_name.lower() != original_text.lower():
                all_terms.append(canonical_name)
            for term in self._extract_medical_terms(original_text):
                all_terms.append(term)
            for term in self._extract_medical_terms(canonical_name):
                all_terms.append(term)
        
        # Remove duplicates while preserving order
        unique_terms = []
        seen = set()
        for term in all_terms:
            term_lower = term.lower().strip()
            if term_lower and term_lower not in seen and len(term_lower) > 2:
                seen.add(term_lower)
                unique_terms.append(term)
        
        logger.info(f"Retrieving definitions for {len(unique_terms)} unique medical terms")
        
        # Step 1: Try UMLS retrieval (authoritative source) - reuse SpacyExtractor
        umls_definitions = {}
        if self.use_umls and self.spacy_component and medical_report:
            try:
                # Use SpacyExtractor to extract UMLS definitions (reuses existing component)
                umls_terms = self.spacy_component.extract_entities(medical_report)
                
                # Filter by confidence and format for prompt
                for entity in umls_terms:
                    confidence = getattr(entity, "confidence", 0.0) or 0.0
                    if confidence >= self.umls_min_confidence:
                        original_text = (getattr(entity, "original_text", "") or "").lower()
                        definition = getattr(entity, "definition", "") or ""
                        canonical_name = (getattr(entity, "canonical_name", "") or "")

                        if definition and original_text:
                            # Format: use canonical name if different from original
                            if canonical_name and canonical_name.lower() != original_text:
                                umls_definitions[original_text] = f"{canonical_name}: {definition}"
                            else:
                                umls_definitions[original_text] = definition

                        # Stop if we have enough
                        if len(umls_definitions) >= max_definitions * 2:
                            break
                
                logger.info(f"Retrieved {len(umls_definitions)} definitions from UMLS (via SpacyExtractor)")
            except Exception as e:
                logger.warning(f"UMLS retrieval failed: {str(e)}. Falling back to dataset.")
        
        # Step 2: Fill gaps with dataset (plain language translations)
        self._ensure_glossary_loaded()
        dataset_definitions = {}
        
        # Find terms that need definitions
        terms_needing_definitions = set(unique_terms)
        if umls_definitions:
            # Remove terms we already have from UMLS
            terms_needing_definitions -= set(umls_definitions.keys())
        
        if terms_needing_definitions:
            dataset_definitions = self.glossary_builder.search_terms(
                list(terms_needing_definitions),
                threshold=75
            )
            logger.info(f"Retrieved {len(dataset_definitions)} definitions from dataset")
        
        # Step 3: If still missing, try direct dataset search
        if len(definitions) < max_definitions and medical_report:
            missing_terms = set(unique_terms) - set(umls_definitions.keys()) - set(dataset_definitions.keys())
            for term in list(missing_terms)[:10]:  # Try top 10 missing terms
                records = self.glossary_builder.get_dataset_records(term, limit=1)
                if records:
                    dataset_definitions[term] = records[0].get('plain_language_text', '')
        
        # Step 4: Combine results (UMLS first, then dataset)
        # Prioritize UMLS for authoritative definitions
        definitions.update(umls_definitions)
        
        # Add dataset definitions for terms not in UMLS
        for term, definition in dataset_definitions.items():
            if term not in definitions:
                definitions[term] = definition
        
        # Step 5: Limit and prioritize
        if len(definitions) > max_definitions:
            prioritized = {}

            # First: terms that directly appeared in the extracted entities
            for entity in extracted_entities.entities:
                for term in (getattr(entity, "original_text", ""), getattr(entity, "canonical_name", "")):
                    term_lower = term.lower().strip() if term else ""
                    if term_lower and term_lower in definitions and term not in prioritized:
                        prioritized[term] = definitions[term_lower]
                        if len(prioritized) >= max_definitions:
                            break
                if len(prioritized) >= max_definitions:
                    break

            # Second: remaining UMLS definitions (authoritative)
            if len(prioritized) < max_definitions:
                for term, definition in definitions.items():
                    if len(prioritized) >= max_definitions:
                        break
                    if term not in prioritized and term in umls_definitions:
                        prioritized[term] = definition

            # Third: remaining dataset definitions
            if len(prioritized) < max_definitions:
                for term, definition in definitions.items():
                    if len(prioritized) >= max_definitions:
                        break
                    if term not in prioritized:
                        prioritized[term] = definition

            definitions = prioritized
        
        logger.info(f"Retrieved {len(definitions)} total medical term definitions "
                   f"(UMLS: {len(umls_definitions)}, Dataset: {len(dataset_definitions)})")
        
        return definitions
