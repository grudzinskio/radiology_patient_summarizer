"""
RAG (Retrieval-Augmented Generation) Service for medical term definitions.

This service retrieves trusted, standardized definitions for medical terms
using a multi-source approach:
1. UMLS (Unified Medical Language System) - Authoritative medical definitions
   (Reuses SpacyComponent from entity_extraction to avoid duplication)
2. PLABA/Cochrane datasets - Plain language translations

Provides a "Definitions Context" for the summarization pipeline.
"""
import logging
import re
from typing import Dict, List, Optional
from schemas.validation import EntityExtractionResult
from services.summaries.rag.glossary_builder import GlossaryBuilder
from services.summaries.entity_extraction.pipeline_components.spacy_component import SpacyComponent

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG service that retrieves medical term definitions from trusted sources.
    
    Uses a hybrid approach:
    1. UMLS (primary) - Authoritative medical definitions via SpacyComponent (reuses existing component)
    2. PLABA/Cochrane datasets (fallback) - Plain language translations
    
    Trigger: Takes the list of medical terms from Step 1 (Entity Extraction)
    Action: Searches UMLS (via SpacyComponent) and trusted medical glossary
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
        
        # Reuse SpacyComponent from entity_extraction (avoids duplication)
        if self.use_umls:
            try:
                self.spacy_component = SpacyComponent()
                logger.info("UMLS retriever initialized (using SpacyComponent)")
            except Exception as e:
                logger.warning(f"Could not initialize SpacyComponent: {str(e)}. Will use dataset only.")
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
        1. UMLS (primary) - Authoritative medical definitions via SpacyComponent
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
        
        # Add findings (these are the main medical terms)
        all_terms.extend(extracted_entities.findings)
        
        # Add anatomy terms
        all_terms.extend(extracted_entities.anatomy)
        
        # Extract additional terms from entity strings
        for finding in extracted_entities.findings:
            terms = self._extract_medical_terms(finding)
            all_terms.extend(terms)
        
        for anatomy in extracted_entities.anatomy:
            terms = self._extract_medical_terms(anatomy)
            all_terms.extend(terms)
        
        # Remove duplicates while preserving order
        unique_terms = []
        seen = set()
        for term in all_terms:
            term_lower = term.lower().strip()
            if term_lower and term_lower not in seen and len(term_lower) > 2:
                seen.add(term_lower)
                unique_terms.append(term)
        
        logger.info(f"Retrieving definitions for {len(unique_terms)} unique medical terms")
        
        # Step 1: Try UMLS retrieval (authoritative source) - reuse SpacyComponent
        umls_definitions = {}
        if self.use_umls and self.spacy_component and medical_report:
            try:
                # Use SpacyComponent to extract UMLS definitions (reuses existing component)
                umls_terms = self.spacy_component.extract_technical_terms(medical_report)
                
                # Filter by confidence and format for prompt
                for term_dict in umls_terms:
                    confidence = term_dict.get("confidence", 0.0)
                    if confidence >= self.umls_min_confidence:
                        original_text = term_dict.get("original_text", "").lower()
                        definition = term_dict.get("definition", "")
                        canonical_name = term_dict.get("canonical_name", "")
                        
                        if definition and original_text:
                            # Format: use canonical name if different from original
                            if canonical_name and canonical_name.lower() != original_text:
                                umls_definitions[original_text] = f"{canonical_name}: {definition}"
                            else:
                                umls_definitions[original_text] = definition
                        
                        # Stop if we have enough
                        if len(umls_definitions) >= max_definitions * 2:
                            break
                
                logger.info(f"Retrieved {len(umls_definitions)} definitions from UMLS (via SpacyComponent)")
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
            # Prioritize: findings > anatomy > other terms
            prioritized = {}
            
            # First: findings from UMLS or dataset
            for finding in extracted_entities.findings:
                finding_lower = finding.lower().strip()
                if finding_lower in definitions:
                    prioritized[finding] = definitions[finding_lower]
            
            # Second: anatomy terms
            for anatomy in extracted_entities.anatomy:
                anatomy_lower = anatomy.lower().strip()
                if anatomy_lower in definitions and anatomy_lower not in prioritized:
                    prioritized[anatomy] = definitions[anatomy_lower]
            
            # Third: remaining UMLS definitions (authoritative)
            for term, definition in definitions.items():
                if len(prioritized) >= max_definitions:
                    break
                if term not in prioritized:
                    # Check if this came from UMLS (prioritize authoritative sources)
                    if term in umls_definitions:
                        prioritized[term] = definition
            
            # Fourth: remaining dataset definitions
            for term, definition in definitions.items():
                if len(prioritized) >= max_definitions:
                    break
                if term not in prioritized:
                    prioritized[term] = definition
            
            definitions = prioritized
        
        logger.info(f"Retrieved {len(definitions)} total medical term definitions "
                   f"(UMLS: {len(umls_definitions)}, Dataset: {len(dataset_definitions)})")
        
        return definitions
