"""
RAG (Retrieval-Augmented Generation) Service for medical term definitions.

This service retrieves trusted, standardized definitions for medical terms
from the PLABA and Cochrane datasets, providing a "Definitions Context"
for the summarization pipeline.
"""
import logging
import re
from typing import Dict, List, Optional
from backend.app.schemas.validation import EntityExtractionResult
from backend.app.services.summaries.rag.glossary_builder import GlossaryBuilder

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG service that retrieves medical term definitions from trusted sources.
    
    Trigger: Takes the list of medical terms from Step 1 (Entity Extraction)
    Action: Searches a trusted "Medical Glossary" built from PLABA/Cochrane datasets
    Output: A "Definitions Context" dictionary to feed into the next step
    """
    
    def __init__(self, dataset_path: Optional[str] = None, preferred_sources: Optional[List[str]] = None):
        """
        Initialize the RAG service.
        
        Args:
            dataset_path: Path to the merged_plain_language_dataset.csv file
            preferred_sources: Preferred source datasets (default: ['PLABA', 'Cochrane'])
        """
        if preferred_sources is None:
            preferred_sources = ['PLABA', 'Cochrane']
        
        self.preferred_sources = preferred_sources
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
        
        This is the main RAG pipeline step:
        - Takes entities from Step 1 (Entity Extraction)
        - Searches trusted medical glossary
        - Returns definitions context for Step 2 (Summarization)
        
        Args:
            extracted_entities: EntityExtractionResult from Step 1
            medical_report: Optional original medical report for additional context
            max_definitions: Maximum number of definitions to return
        
        Returns:
            Dictionary mapping medical terms to their plain language definitions
        """
        self._ensure_glossary_loaded()
        
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
        
        # Also extract terms from the original report if provided
        if medical_report:
            report_terms = self._extract_medical_terms(medical_report)
            all_terms.extend(report_terms)
        
        # Remove duplicates while preserving order
        unique_terms = []
        seen = set()
        for term in all_terms:
            term_lower = term.lower().strip()
            if term_lower and term_lower not in seen and len(term_lower) > 2:
                seen.add(term_lower)
                unique_terms.append(term)
        
        logger.info(f"Retrieving definitions for {len(unique_terms)} unique medical terms")
        
        # Search for definitions
        definitions = self.glossary_builder.search_terms(unique_terms, threshold=75)
        
        # If we have fewer definitions than requested, try searching the dataset directly
        if len(definitions) < max_definitions and medical_report:
            # Try to find contextual matches in the dataset
            for term in unique_terms[:10]:  # Try top 10 terms
                if term not in definitions:
                    records = self.glossary_builder.get_dataset_records(term, limit=1)
                    if records:
                        # Use the plain language text as definition
                        definitions[term] = records[0].get('plain_language_text', '')
        
        # Limit to max_definitions
        if len(definitions) > max_definitions:
            # Keep the most relevant ones (prioritize exact matches from findings)
            prioritized = {}
            for finding in extracted_entities.findings:
                finding_lower = finding.lower().strip()
                if finding_lower in definitions:
                    prioritized[finding] = definitions[finding_lower]
            
            # Add remaining definitions
            for term, definition in definitions.items():
                if len(prioritized) >= max_definitions:
                    break
                if term not in prioritized:
                    prioritized[term] = definition
            
            definitions = prioritized
        
        logger.info(f"Retrieved {len(definitions)} medical term definitions")
        
        return definitions
