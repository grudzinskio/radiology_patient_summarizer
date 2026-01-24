from typing import Any, TypedDict
from pathlib import Path
import time


from langgraph.graph import END, StateGraph
from schemas.validation import EntityExtractionResult, ValidationInput, ValidationReport
import logging

logger = logging.getLogger(__name__)

from schemas.provenance import ProvenanceReport, SummaryWithProvenance
from services.summaries.entity_extraction.pipeline import EntityExtractionPipeline
from services.summaries.summarizer import SummarizerAgent
from services.summaries.validation.pipeline import ValidationPipeline
from services.summaries.validation.readability import ReadabilityComponent
from services.summaries.validation.safety import SafetyComponent
from services.summaries.validation.hallucination import HallucinationComponent
from services.summaries.validation.fidelity import FidelityComponent
from services.summaries.validation.entity_matching import EntityMatchingComponent
from services.summaries.validation.provenance import ProvenanceComponent
from services.summaries.refiner import RefinerAgent
from services.summaries.rag_service import RAGService

class ChainOfThoughtStep(TypedDict):
    """
    Represents a single step in the agent's reasoning process.
    """
    step: str
    description: str
    details: dict[str, Any] | None
    timestamp: float


class PlainLanguageReportAgentState(TypedDict):
    """
    State for the PlainLanguageReportAgent graph.
    Carries all data through the summarization, validation, and refinement pipeline.
    """
    # Input fields
    medical_report: str
    patient_id: str | None
    report_id: str | None
    
    # Extraction results
    extracted_entities: EntityExtractionResult | None
    retrieved_definitions: dict[str, str] | None
    
    # Summary output
    plain_language_report: str | None
    
    # Provenance and explainability (NEW)
    summary_with_provenance: SummaryWithProvenance | None
    provenance_report: ProvenanceReport | None
    overall_confidence: float
    
    # Validation results
    validation_passed: bool
    validation_reasons: list[str]
    validation_pipeline_result: ValidationReport | None


    
    # Reasoning trace
    chain_of_thought: list[ChainOfThoughtStep]



class PlainLanguageReportAgent:
    """
    Agent that orchestrates the full summarization pipeline with validation and provenance tracking.
    
    Pipeline:
    1. Entity Extraction: Extract medical entities from the report
    2. Summarization: Generate a patient-friendly summary with citations
    3. Validation: Verify fidelity, check for hallucinations, assess readability, safety, and provenance
    4. Refinement: If validation fails, refine the summary and re-validate
    """
    
    def __init__(self, enable_provenance: bool = True, dataset_path: str | None = None):
        """
        Initialize the agent.
        
        Args:
            enable_provenance: Whether to enable provenance tracking (default: True)
        """
        self.enable_provenance = enable_provenance
        logger.info(f"Initializing Agent (provenance={enable_provenance})...")

        """
        Initialize the plain language report agent.
        
        Args:
            dataset_path: Path to merged_plain_language_dataset.csv. If None, 
                         tries to find it in the repo root.
        """
        self.entity_extraction_pipeline = EntityExtractionPipeline()
        self.summarization_agent = SummarizerAgent()
        
        logger.info("Initializing Validation Pipeline...")
        # Build validation pipeline with provenance component

        validation_components = [
            ReadabilityComponent(),
            SafetyComponent(),
            HallucinationComponent(),
            FidelityComponent(),
            EntityMatchingComponent(),
        ]
        
        if enable_provenance:
            validation_components.append(ProvenanceComponent())
        
        self.validation_pipeline = ValidationPipeline(components=validation_components)
        self.refiner_agent = RefinerAgent()
        
        # Initialize RAG service
        if dataset_path is None:
            # Try to find dataset in repo root
            # Current file: backend/src/services/summaries/plain_language_report_agent.py
            # 5 parents up to reach hack-4-health-2026-radiohead
            repo_root = Path(__file__).parent.parent.parent.parent.parent
            dataset_path = str(repo_root / "merged_plain_language_dataset.csv")
        
        self.rag_service = RAGService(dataset_path=dataset_path)
        self.graph = self._build_agent_graph()
        logger.info("Agent initialization complete.")


    def _create_initial_state(
        self, 
        medical_report: str, 
        patient_id: str | None = None, 
        report_id: str | None = None
    ) -> PlainLanguageReportAgentState:
        """Create the initial state for the agent graph."""
        return PlainLanguageReportAgentState(
            medical_report=medical_report,
            patient_id=patient_id,
            report_id=report_id,
            extracted_entities=EntityExtractionResult(),
            retrieved_definitions=None,
            plain_language_report=None,
            summary_with_provenance=None,
            provenance_report=None,
            overall_confidence=0.0,
            validation_passed=False,
            validation_reasons=[],
            validation_pipeline_result=None,

            chain_of_thought=[],
        )



    def run(
        self, 
        medical_report: str, 
        patient_id: str | None = None, 
        report_id: str | None = None
    ) -> PlainLanguageReportAgentState:
        """
        Run the plain-language report agent.
        
        Args:
            medical_report: The original medical/radiology report text
            patient_id: Optional patient identifier
            report_id: Optional report identifier
            
        Returns:
            The final state containing the summary, provenance, and validation results
        """
        state = self._create_initial_state(medical_report, patient_id, report_id)
        return self.graph.invoke(state)

    @staticmethod
    def _validation_gate(state: PlainLanguageReportAgentState) -> str:
        """Gate function to determine if refinement is needed."""
        return END if state["validation_passed"] else "refiner_agent"

    def _build_agent_graph(self):
        """
        Build the agent graph.

        Pipeline flow:
        1. Entity Extraction: Extract important medical entities
        RAG retrieves definitions for medical terms ->
        2. Summarization: Generate summary with provenance citations
        3. Validation: Run all validation checks including provenance verification
        4. Refinement (if needed): Refine summary based on validation feedback
        5. Re-validation: Loop until validation passes
        """
        graph = StateGraph(PlainLanguageReportAgentState)
        graph.add_node("entity_extraction_pipeline", self._extraction_node)
        graph.add_node("rag_retrieval", self._rag_retrieval_node)
        graph.add_node("summarization_agent", self._summarization_node)
        graph.add_node("validation_pipeline", self._validation_node)
        graph.add_node("refiner_agent", self._refinement_node)

        graph.set_entry_point("entity_extraction_pipeline")
        graph.add_edge("entity_extraction_pipeline", "rag_retrieval")
        graph.add_edge("rag_retrieval", "summarization_agent")
        graph.add_edge("summarization_agent", "validation_pipeline")
        graph.add_conditional_edges(
            "validation_pipeline",
            self._validation_gate,
            {"refiner_agent": "refiner_agent", END: END},
        )
        graph.add_edge("refiner_agent", "validation_pipeline")

        return graph.compile()

    def _build_basic_graph(self):
        """
        Build the agent graph for the basic summarization process.

        Medical Report is summarized ->
        Plain Language Report is returned

        Used as MVP and Baseline Model for the summarization process.
        """
        graph = StateGraph(PlainLanguageReportAgentState)
        graph.add_node("summarization_agent", self._summarization_node)
        graph.set_entry_point("summarization_agent")
        graph.add_edge("summarization_agent", END)
        return graph.compile()

    def _extraction_node(self, state: PlainLanguageReportAgentState) -> dict[str, Any]:
        """Extract medical entities from the report."""
        logger.info("Starting Entity Extraction node")
        
        try:
            raw_terms = self.entity_extraction_pipeline.extract_entities(state["medical_report"])
        except Exception as e:
            logger.error(f"Error in entity extraction: {e}")
            raw_terms = []

        findings = [
            term.get("original_text", "") for term in raw_terms if term.get("original_text")
        ] if isinstance(raw_terms, list) else []

        extracted_entities = EntityExtractionResult(findings=findings)
        
        # Log the extraction step
        current_log = state.get("chain_of_thought", [])
        log_step = ChainOfThoughtStep(
            step="Entity Extraction",
            description=f"Identified {len(findings)} medical entities from the report.",
            details={
                "found_entities_count": len(findings),
                "entities_sample": findings[:5] if findings else []
            },
            timestamp=time.time()
        )
        
        return {
            "extracted_entities": extracted_entities, 
            "chain_of_thought": current_log + [log_step]
        }


    def _rag_retrieval_node(self, state: PlainLanguageReportAgentState) -> dict[str, Any]:
        """
        Retrieve medical term definitions using RAG service.
        """
        logger.info("Starting RAG Retrieval node")
        extracted_entities = state["extracted_entities"] or EntityExtractionResult()

        
        # Log intent before action
        initial_log = state.get("chain_of_thought", [])
        
        retrieved_definitions = self.rag_service.retrieve_definitions(
            extracted_entities=extracted_entities,
            medical_report=state["medical_report"],
            max_definitions=20
        )
        
        # Log the retrieval step
        log_step = ChainOfThoughtStep(
            step="Knowledge Retrieval",
            description=f"Retrieved definitions for {len(retrieved_definitions)} medical terms to aid understanding.",
            details={
                "terms_defined": list(retrieved_definitions.keys()),
                "retrieval_count": len(retrieved_definitions)
            },
            timestamp=time.time()
        )
        
        return {
            "retrieved_definitions": retrieved_definitions,
            "chain_of_thought": initial_log + [log_step]
        }

    def _summarization_node(self, state: PlainLanguageReportAgentState) -> dict[str, Any]:
        """Generate a patient-friendly summary with provenance tracking."""
        logger.info("Starting Summarization node")
        extracted_entities = state["extracted_entities"] or EntityExtractionResult()

        current_log = state.get("chain_of_thought", [])
        
        if self.enable_provenance:
            # Use provenance-aware summarization
            summary_with_prov = self.summarization_agent.generate_summary_with_provenance(
                original_report=state["medical_report"],
                extracted_entities=extracted_entities,
                retrieved_definitions=state["retrieved_definitions"],
            )
            
            log_step = ChainOfThoughtStep(
                step="Summarization",
                description="Generated initial patient-friendly summary with provenance citations.",
                details={
                    "mode": "provenance",
                    "sentence_count": len(summary_with_prov.statements),
                    "confidence_score": summary_with_prov.provenance.overall_confidence if summary_with_prov.provenance else 0.0
                },
                timestamp=time.time()
            )
            
            return {
                "plain_language_report": summary_with_prov.plain_language_report,
                "summary_with_provenance": summary_with_prov,
                "provenance_report": summary_with_prov.provenance,
                "chain_of_thought": current_log + [log_step]
            }
        else:
            # Standard summarization without provenance
            plain_language_report = self.summarization_agent.generate_summary(
                original_report=state["medical_report"],
                extracted_entities=extracted_entities,
                retrieved_definitions=state["retrieved_definitions"],
            )
            
            log_step = ChainOfThoughtStep(
                step="Summarization",
                description="Generated initial patient-friendly summary (standard mode).",
                details={
                    "mode": "standard",
                    "length_chars": len(plain_language_report)
                },
                timestamp=time.time()
            )
            
            return {
                "plain_language_report": plain_language_report, 
                "chain_of_thought": current_log + [log_step]
            }

    def _validation_node(self, state: PlainLanguageReportAgentState) -> dict[str, Any]:
        """Run validation checks on the summary."""
        logger.info("Starting Validation node")
        validation_input = ValidationInput(
            original_report=state["medical_report"],
            extracted_entities=state["extracted_entities"] or EntityExtractionResult(),
            draft_summary=state["plain_language_report"] or "",
            retrieved_definitions=state["retrieved_definitions"],
        )
        
        # Attach existing provenance if available (for ProvenanceComponent to verify)
        if state.get("summary_with_provenance"):
            validation_input._summary_with_provenance = state["summary_with_provenance"]
        
        report = self.validation_pipeline.validate(validation_input)
        
        # Extract provenance report from validation input if it was updated
        provenance_report = None
        overall_confidence = 0.0
        
        if hasattr(validation_input, '_provenance_report'):
            provenance_report = validation_input._provenance_report
            overall_confidence = provenance_report.overall_confidence
        elif state.get("provenance_report"):
            provenance_report = state["provenance_report"]
            overall_confidence = provenance_report.overall_confidence
        
        # Log validation results
        current_log = state.get("chain_of_thought", [])
        
        if report.overall_passed:
            description = "Validation passed. Summary meets all safety and accuracy criteria."
        else:
            description = f"Validation failed with {len(report.get_all_errors())} issues. Initiating refinement."
            
        log_step = ChainOfThoughtStep(
            step="Validation",
            description=description,
            details={
                "passed": report.overall_passed,
                "overall_confidence": overall_confidence,
                "failed_components": [r.component_name for r in report.get_failed_components()],
                "error_count": len(report.get_all_errors())
            },
            timestamp=time.time()
        )
        
        return {
            "validation_pipeline_result": report,
            "validation_passed": report.overall_passed,
            "validation_reasons": report.get_all_errors(),
            "provenance_report": provenance_report,
            "overall_confidence": overall_confidence,
            "chain_of_thought": current_log + [log_step]
        }

    def _refinement_node(self, state: PlainLanguageReportAgentState) -> dict[str, Any]:
        """Refine the summary based on validation feedback."""
        logger.info("Starting Refinement node due to validation failure")
        plain_language_report = self.refiner_agent.refine_summary(
            original_report=state["medical_report"],
            extracted_entities=state["extracted_entities"] or EntityExtractionResult(),
            current_summary=state["plain_language_report"],
            validation_report=state["validation_pipeline_result"],
            retrieved_definitions=state["retrieved_definitions"],
        )
        
        # Re-create provenance from refined summary
        summary_with_prov = SummaryWithProvenance.from_text(plain_language_report)
        
        # Log refinement
        current_log = state.get("chain_of_thought", [])
        log_step = ChainOfThoughtStep(
            step="Refinement",
            description="Refined summary to address validation errors.",
            details={
                "previous_errors": [r.component_name for r in state["validation_pipeline_result"].get_failed_components()],
                "action": "rewrite_and_revalidate"
            },
            timestamp=time.time()
        )
        
        return {
            "plain_language_report": plain_language_report,
            "summary_with_provenance": summary_with_prov,
            "provenance_report": summary_with_prov.provenance,
            "chain_of_thought": current_log + [log_step]
        }

