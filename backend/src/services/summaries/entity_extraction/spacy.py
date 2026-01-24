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
    section: Optional[str]  # Which section of the report (findings, impression, etc.)
    is_negated: bool  # "No evidence of pneumonia" -> negated=True
    is_uncertain: bool  # "Possible nodule" -> uncertain=True
    is_family: bool  # "Mother has history of cancer" -> family=True
    is_historical: bool  # Past medical history vs current finding
    
    # Position in text
    start_char: int
    end_char: int
    
    # MeSH identifiers
    mesh_id: str
    aliases: list[str]  # Alternative names for the concept


class SpacyExtractor:
    """
    Component for extracting clinical entities from radiology reports using SciSpacy and MedSpacy.
    Provides entity linking, negation detection, and section awareness.
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
        'T023',  # Body Part, Organ, or Organ Component (useful for anatomy)
        'T031',  # Body Substance (blood, fluid, etc.)
    }
    
    @classmethod
    def load_model(cls):
        """Explicitly load the model (e.g., at startup). Returns the singleton NLP instance."""
        global _NLP_INSTANCE
        if _NLP_INSTANCE is None:
            logger.info("Loading SciSpacy model...")
            nlp = spacy.load("en_core_sci_md")

            logger.info("Adding MedSpaCy components...")
            # Context detection (negation, uncertainty, family history, etc.)
            nlp.add_pipe("medspacy_context")
            
            # Section detection (Findings, Impression, History, etc.)
            nlp.add_pipe("medspacy_sectionizer")
            
            # Post-processing and cleanup
            nlp.add_pipe("medspacy_postprocessor")

            logger.info("Adding MESH entity linker...")
            nlp.add_pipe("scispacy_linker", config={
                "resolve_abbreviations": True, 
                "linker_name": "mesh"
            })

            logger.info("SpacyExtractor model loaded successfully.")
            _NLP_INSTANCE = nlp
        return _NLP_INSTANCE

    def __init__(self):
        global _NLP_INSTANCE
        if _NLP_INSTANCE is None:
            self.nlp = self.load_model()
        else:
            self.nlp = _NLP_INSTANCE
        
        # Linker is already in the pipeline
        self.linker = self.nlp.get_pipe("scispacy_linker")

    def extract_entities(self, report: str, include_negated: bool = False) -> list[ClinicalEntity]:
        """
        Extract clinical entities with full context from a radiology report.
        
        Args:
            report: The radiology report text
            include_negated: Whether to include negated findings (e.g., "No pneumonia")
                           Default False - typically we only want positive findings
        
        Returns:
            List of ClinicalEntity objects with clinical context
        """
        doc = self.nlp(report)
        
        entities = []
        for ent in doc.ents:
            # Skip entities without MeSH links
            if not ent._.kb_ents:
                logger.debug(f"No MeSH link for: {ent.text}")
                continue
            
            # Get top MeSH match
            mesh_id, score = ent._.kb_ents[0]
            concept = self.linker.kb.cui_to_entity[mesh_id]
            
            # Filter for clinically relevant types
            has_clinical_type = any(t in self.CLINICAL_TYPES for t in concept.types)
            if not has_clinical_type:
                logger.debug(f"Skipping non-clinical entity: {ent.text} ({concept.types})")
                continue
            
            # Skip negated findings unless explicitly requested
            if ent._.is_negated and not include_negated:
                logger.debug(f"Skipping negated entity: {ent.text}")
                continue
            
            # Skip family history unless explicitly requested
            if ent._.is_family:
                logger.debug(f"Skipping family history: {ent.text}")
                continue
            
            entities.append(ClinicalEntity(
                original_text=ent.text,
                canonical_name=concept.canonical_name,
                definition=concept.definition,
                semantic_types=list(concept.types),
                confidence=score,
                
                # MedSpaCy context
                section=ent._.section_category,
                is_negated=ent._.is_negated,
                is_uncertain=ent._.is_uncertain,
                is_family=ent._.is_family,
                is_historical=ent._.is_historical,
                
                # Position
                start_char=ent.start_char,
                end_char=ent.end_char,
                
                # MeSH metadata
                mesh_id=mesh_id,
                aliases=list(concept.aliases)[:5]  # First 5 aliases
            ))
        
        # Deduplicate: keep highest confidence entity per (canonical_name, section, negation status)
        seen = {}
        for ent in entities:
            # Key by canonical name, section, and negation status
            # This allows "pneumonia" in findings vs impression to be separate
            # but merges "brain" -> "Brain" duplicates in same section
            key = (ent.canonical_name, ent.section, ent.is_negated, ent.is_uncertain)
            
            if key not in seen or ent.confidence > seen[key].confidence:
                seen[key] = ent
        
        deduped = list(seen.values())
        
        if len(entities) > len(deduped):
            logger.debug(f"Deduplicated {len(entities)} -> {len(deduped)} entities")
        
        return deduped

    def extract_technical_terms(self, report: str) -> list[dict]:
        """
        Extract technical terms and their lay-friendly definitions (legacy method).
        Returns simplified dict format for backward compatibility.
        """
        entities = self.extract_entities(report, include_negated=False)
        
        terms = []
        for ent in entities:
            terms.append({
                "original_text": ent.original_text,
                "canonical_name": ent.canonical_name,
                "definition": ent.definition,
                "semantic_types": ent.semantic_types,
                "confidence": ent.confidence
            })
        
        return terms

    def get_findings_only(self, report: str) -> list[ClinicalEntity]:
        """Extract only current findings (exclude history, family, negated)."""
        entities = self.extract_entities(report, include_negated=False)
        
        # Filter to findings/impression sections and current (non-historical) findings
        findings = [
            e for e in entities 
            if not e.is_historical 
            and e.section in [None, 'findings', 'impression', 'conclusion']
        ]
        
        return findings

    def get_critical_findings(self, report: str, min_confidence: float = 0.85) -> list[ClinicalEntity]:
        """
        Extract high-confidence, urgent findings that need patient attention.
        Filters for uncertain and historical findings.
        """
        entities = self.get_findings_only(report)
        
        # High confidence, not uncertain
        critical = [
            e for e in entities
            if e.confidence >= min_confidence
            and not e.is_uncertain
        ]
        
        return critical

    def build_simplification_context(self, report: str) -> str:
        """
        Build structured context for an LLM to simplify the report.
        Organizes findings by section and clinical status.
        """
        entities = self.extract_entities(report, include_negated=True)
        
        if not entities:
            return "No significant clinical entities found."
        
        # Group by section
        sections = {}
        for entity in entities:
            section = entity.section or "general"
            if section not in sections:
                sections[section] = {
                    'positive': [],
                    'negative': [],
                    'uncertain': []
                }
            
            if entity.is_negated:
                sections[section]['negative'].append(entity)
            elif entity.is_uncertain:
                sections[section]['uncertain'].append(entity)
            else:
                sections[section]['positive'].append(entity)
        
        # Build context string
        context = "Clinical Entities by Section:\n\n"
        
        for section, entities_dict in sections.items():
            context += f"=== {section.upper()} ===\n"
            
            if entities_dict['positive']:
                context += "Findings:\n"
                for e in entities_dict['positive']:
                    context += f"  • {e.original_text} ({e.canonical_name})\n"
                    if e.definition:
                        context += f"    Definition: {e.definition}\n"
            
            if entities_dict['uncertain']:
                context += "Possible/Uncertain:\n"
                for e in entities_dict['uncertain']:
                    context += f"  • {e.original_text} ({e.canonical_name})\n"
            
            if entities_dict['negative']:
                context += "Ruled Out:\n"
                for e in entities_dict['negative']:
                    context += f"  • {e.original_text}\n"
            
            context += "\n"
        
        return context

    def get_simplification_glossary(self, report: str) -> dict[str, str]:
        """
        Get a simple glossary of technical terms -> plain language.
        Only includes positive findings with definitions.
        """
        entities = self.get_findings_only(report)
        
        glossary = {}
        for entity in entities:
            if entity.definition:
                glossary[entity.original_text] = entity.definition
        
        return glossary

    def get_section_summary(self, report: str) -> dict[str, list[str]]:
        """Get findings organized by report section."""
        entities = self.get_findings_only(report)
        
        summary = {}
        for entity in entities:
            section = entity.section or "general"
            if section not in summary:
                summary[section] = []
            
            status = ""
            if entity.is_uncertain:
                status = "[Possible] "
            
            summary[section].append(f"{status}{entity.canonical_name}")
        
        return summary