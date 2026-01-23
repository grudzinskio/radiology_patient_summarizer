import spacy
from scispacy.linking import EntityLinker

class EntityExtractionPipeline:
    """
    Pipeline for extracting technical terms from a medical report
    """
    def __init__(self):
        self.pipeline = self._build_pipeline()
    
    def _build_pipeline(self):
        """
        Build the pipeline for extracting technical terms from a medical report
        """
        return self.pipeline

    def extract_technical_terms(report: str) -> list[dict]:
        """Extract technical terms and their lay-friendly definitions."""
        
        nlp = spacy.load("en_core_sci_md")
        nlp.add_pipe("scispacy_linker", config={"resolve_abbreviations": True, "linker_name": "umls"})
        linker = nlp.get_pipe("scispacy_linker")
        
        doc = nlp(report)
        
        terms = []
        for ent in doc.ents:
            if ent._.kb_ents:
                cui, score = ent._.kb_ents[0]  # Top match
                concept = linker.kb.cui_to_entity[cui]
                
                terms.append({
                    "original_text": ent.text,
                    "canonical_name": concept.canonical_name,
                    "definition": concept.definition,
                    "semantic_types": concept.types,
                    "confidence": score
                })
        
        return terms


    def build_simplification_context(report: str) -> str:
        """Build context for an LLM to simplify the report."""
        
        terms = extract_technical_terms(report)
        
        context = "Technical terms and their meanings:\n"
        for term in terms:
            if term["definition"]:
                context += f"- {term['original_text']}: {term['definition']}\n"
        
        return context