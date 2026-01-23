import spacy
from scispacy.linking import EntityLinker
from typing import List
from backend.app.services.summaries.validation.pipeline_components.pipeline_component import PipelineComponent
import logging
from backend.app.services.summaries.entity_extraction.pipeline_components.spacy_component import SpacyComponent

logger = logging.getLogger(__name__)

class EntityExtractionPipeline:
    """
    Pipeline for extracting technical terms from a medical report
    
    Currently utilizes the SpacyComponent to extract technical terms from the report and link them to the UMLS for LLM context building.
    """
    def __init__(self):
        self.spacy_component = SpacyComponent()
    
    def extract_entities(self, report: str):
        """
        Extract entities from the report through the pipeline.
        """
        extracted_entities = self.spacy_component.extract_technical_terms(report)
        return extracted_entities

    def build_simplification_context(self, report: str):
        """
        Build context for an LLM to simplify the report.
        """
        simplified_context = self.spacy_component.build_simplification_context(report)
        return simplified_context