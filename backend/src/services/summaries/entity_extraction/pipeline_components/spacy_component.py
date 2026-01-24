from imaplib import ParseFlags
from typing import Any
import logging
import spacy
from scispacy.linking import EntityLinker
import scispacy

logger = logging.getLogger(__name__)

_NLP_INSTANCE = None

class SpacyComponent():
    """
    Component for extracting entities from a text using Spacy.
    Uses a singleton pattern for the heavy NLP model.
    """
    @classmethod
    def load_model(cls):
        """Explicitly load the model (e.g., at startup)."""
        global _NLP_INSTANCE
        if _NLP_INSTANCE is None:
            logger.info("Loading Spacy model...")
            nlp = spacy.load("en_core_sci_sm")
            nlp.add_pipe("scispacy_linker", config={"resolve_abbreviations": True, "linker_name": "umls"})
            _NLP_INSTANCE = nlp
            logger.info("Spacy model loaded successfully.")
        return _NLP_INSTANCE

    def __init__(self):
        global _NLP_INSTANCE
        if _NLP_INSTANCE is None:
            self.nlp = self.load_model()
        else:
            self.nlp = _NLP_INSTANCE
        
        # Linker is already in the pipeline
        self.linker = self.nlp.get_pipe("scispacy_linker")


    def extract_technical_terms(self, report: str) -> list[dict]:
        """Extract technical terms and their lay-friendly definitions."""
        
        doc = self.nlp(report)
        
        terms = []
        for ent in doc.ents:
            if ent._.kb_ents:
                cui, score = ent._.kb_ents[0]  # Top match
                concept = self.linker.kb.cui_to_entity[cui]
                
                terms.append({
                    "original_text": ent.text,
                    "canonical_name": concept.canonical_name,
                    "definition": concept.definition,
                    "semantic_types": concept.types,
                    "confidence": score
                })
        
        return terms


    def build_simplification_context(self, report: str) -> str:
        """Build context for an LLM to simplify the report."""
        
        terms = self.extract_technical_terms(report)
        
        context = "Technical terms and their meanings:\n"
        for term in terms:
            if term["definition"]:
                context += f"- {term['original_text']}: {term['definition']}\n"
        
        return context