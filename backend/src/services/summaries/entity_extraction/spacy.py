from typing import Optional
import logging
import spacy
from scispacy.linking import EntityLinker
import scispacy
import medspacy
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_NLP_INSTANCE = None

@dataclass
class ClinicalEntity:
    """Structured representation of a clinical entity with context."""
    original_text: str
    canonical_name: str
    definition: Optional[str]
    semantic_types: list[str]
    confidence: float
    
    # MedSpaCy context attributes
    section: Optional[str]
    is_negated: bool
    is_uncertain: bool
    is_family: bool
    is_historical: bool
    
    # Position in text
    start_char: int
    end_char: int
    
    # MeSH identifiers
    mesh_id: str
    aliases: list[str]


class SpacyComponent:
    """
    Component for extracting clinical entities from radiology reports.
    Uses a singleton pattern for the heavy NLP model.
    """
    
    # Semantic types for clinically relevant entities
    CLINICAL_TYPES = {
        'T047',  # Disease or Syndrome
        'T048',  # Mental or Behavioral Dysfunction
        'T049',  # Cell or Molecular Dysfunction
        'T059',  # Laboratory or Test Result
        'T060',  # Diagnostic Procedure
        'T061',  # Therapeutic or Preventive Procedure
        'T184',  # Sign or Symptom
        'T033',  # Finding
        'T037',  # Injury or Poisoning
        'T046',  # Pathologic Function
        'T191',  # Neoplastic Process
        'T023',  # Body Part, Organ, or Organ Component
        'T031',  # Body Substance
    }
    
    @classmethod
    def load_model(cls):
        """Explicitly load the model (e.g., at startup). Returns the singleton NLP instance."""
        global _NLP_INSTANCE
        if _NLP_INSTANCE is None:
            logger.info("Loading SciSpacy model...")
            nlp = spacy.load("en_core_sci_md")

            logger.info("Adding MedSpaCy components...")
            nlp.add_pipe("medspacy_context")
            nlp.add_pipe("medspacy_sectionizer")
            nlp.add_pipe("medspacy_postprocessor")

            logger.info("Adding MESH entity linker...")
            nlp.add_pipe("scispacy_linker", config={
                "resolve_abbreviations": True, 
                "linker_name": "mesh"
            })

            logger.info("SpacyComponent model loaded successfully.")
            _NLP_INSTANCE = nlp
        return _NLP_INSTANCE

    def __init__(self):
        global _NLP_INSTANCE
        if _NLP_INSTANCE is None:
            self.nlp = self.load_model()
        else:
            self.nlp = _NLP_INSTANCE
        
        self.linker = self.nlp.get_pipe("scispacy_linker")

    def extract_entities(self, report: str) -> list[ClinicalEntity]:
        """
        Extract ALL clinical entities from a radiology report.
        Keeps negated, family history, historical, and uncertain findings.
        
        Args:
            report: The radiology report text
            require_mesh_link: If True, only return entities with MeSH links.
                            If False, keep all entities but mark those without links.
        
        Returns:
            List of ClinicalEntity objects with clinical context
        """
        doc = self.nlp(report)
        
        entities = []
        for ent in doc.ents:
            # Get MeSH info if available
            mesh_id = None
            mesh_score = None
            concept = None
            
            if ent._.kb_ents:
                mesh_id, mesh_score = ent._.kb_ents[0]
                concept = self.linker.kb.cui_to_entity[mesh_id]
                
                # Filter for clinically relevant types only
                has_clinical_type = any(t in self.CLINICAL_TYPES for t in concept.types)
                if not has_clinical_type:
                    logger.debug(f"Skipping non-clinical entity: {ent.text} ({concept.types})")
                    continue

            
            entities.append(ClinicalEntity(
                original_text=ent.text,
                canonical_name=concept.canonical_name if concept else ent.text,
                definition=concept.definition if concept else None,
                semantic_types=list(concept.types) if concept else [],
                confidence=mesh_score if mesh_score else 0.0,
                
                # MedSpaCy context (always available)
                section=ent._.section_category,
                is_negated=ent._.is_negated,
                is_uncertain=ent._.is_uncertain,
                is_family=ent._.is_family,
                is_historical=ent._.is_historical,
                
                # Position
                start_char=ent.start_char,
                end_char=ent.end_char,
                
                # MeSH metadata (may be None)
                mesh_id=mesh_id or "UNKNOWN",
                aliases=list(concept.aliases)[:5] if concept else []
            ))
        
        # Deduplicate
        seen = {}
        for ent in entities:
            key = (ent.canonical_name, ent.section, ent.is_negated, ent.is_uncertain)
            
            if key not in seen or ent.confidence > seen[key].confidence:
                seen[key] = ent
        
        deduped = list(seen.values())
        
        if len(entities) > len(deduped):
            logger.debug(f"Deduplicated {len(entities)} -> {len(deduped)} entities")
        
        return deduped

    def get_section_summary(self, report: str) -> dict[str, list[ClinicalEntity]]:
        """
        Get all entities organized by report section.
        Returns the full ClinicalEntity objects for LLM processing.
        
        Returns:
            Dict mapping section name to list of ClinicalEntity objects
        """
        entities = self.extract_entities(report)
        
        summary = {}
        for entity in entities:
            section = entity.section or "general"
            if section not in summary:
                summary[section] = []
            
            summary[section].append(entity)
        
        return summary