from typing import List
import logging
from .spacy import SpacyExtractor

logger = logging.getLogger(__name__)

class EntityExtractionPipeline:
    """
    Pipeline for extracting technical terms from a medical report
    
    Currently utilizes the SpacyExtractor to extract technical terms from the report and link them to the UMLS for LLM context building.
    """
    def __init__(self):
        self.spacy_component = SpacyExtractor()
    
    def extract_entities(self, report: str):
        """
        Extract entities from the report through the pipeline.
        """
        extracted_entities = self.spacy_component.extract_entities(report)
        return extracted_entities

    def get_section_summary(self, report: str):
        """
        Build context for an LLM to simplify the report.
        """
        simplified_context = self.spacy_component.get_section_summary(report)
        return simplified_context