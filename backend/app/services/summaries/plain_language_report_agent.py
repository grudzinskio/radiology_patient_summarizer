from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from backend.app.services.summaries.entity_extraction.enitity_extraction_pipeline import EntityExtractionPipeline
from backend.app.services.summaries.summarization.summarizer_agent import SummarizationAgent
from backend.app.services.summaries.validation.validation_pipeline import ValidationPipeline
from backend.app.services.summaries.refinement.refiner_agent import RefinerAgent

class PlainLanguageReportAgentState(TypedDict):
    medical_report: str
    patient_id: str | None
    report_id: str | None
    extracted_entities: dict[str, Any] | None
    plain_language_report: str | None
    validation_passed: bool
    validation_reasons: list[str]

class PlainLanguageReportAgent:
    def __init__(self):
        self.entity_extraction_pipeline = EntityExtractionPipeline()
        self.summarization_agent = SummarizationAgent()
        self.validation_pipeline = ValidationPipeline()
        self.refiner_agent = RefinerAgent()
        self.graph = self._build_agent_graph()

    def _create_initial_state(self, medical_report: str, patient_id: str | None = None, report_id: str | None = None) -> PlainLanguageReportAgentState:
        return PlainLanguageReportAgentState(
            medical_report=medical_report,
            patient_id=patient_id,
            report_id=report_id,
            extracted_entities=None,
            plain_language_report=None,
            validation_passed=False,
            validation_reasons=[],
        )

    def run(self, medical_report: str, patient_id: str | None = None, report_id: str | None = None) -> PlainLanguageReportAgentState:
        """
        Run the plain-language report agent.
        """
        state = self._create_initial_state(medical_report, patient_id, report_id)
        return self.graph.invoke(state)

    def _validation_gate(state: PlainLanguageReportAgentState) -> str:
        return END if state["validation_passed"] else "refine"

    def _build_agent_graph(self):
        """
        Build the agent graph.

        Important Medical Entities are extracted ->
        Medical Report is summarized ->
        Validation Pipeline is run -> 
        Refinement Pipeline is run if validation fails ->
        Validation Pipeline is run again until it passes ->
        Plain Language Report is returned
        """

        # After MVP, we will use the following graph:
        # graph = StateGraph(PlainLanguageReportAgentState)
        # graph.add_node("entity_extraction_pipeline", self._extraction_node)
        # graph.add_node("summarization_agent", self._summarization_node)
        # graph.add_node("validation_pipeline", self._validation_node)
        # graph.add_node("refiner_agent", self._refinement_node)

        # graph.set_entry_point("entity_extraction_pipeline")
        # graph.add_edge("entity_extraction_pipeline", "summarization_agent")
        # graph.add_edge("summarization_agent", "validation_pipeline")
        # graph.add_conditional_edges(
        #     "validation_pipeline",
        #     self._validation_gate,
        #     {"refiner_agent": "refiner_agent", END: END},
        # )
        # graph.add_edge("refiner_agent", "validation_pipeline")

        graph = StateGraph(PlainLanguageReportAgentState)
        graph.add_node("summarization_agent", self._summarization_node)
        graph.set_entry_point("summarization_agent")
        graph.add_edge("summarization_agent", END)

        return graph.compile()


    def _extraction_node(self, state: PlainLanguageReportAgentState) -> dict[str, Any]:
        extracted_entities = self.entity_extraction_pipeline.extract_entities(state["medical_report"])
        return {"extracted_entities": extracted_entities}

    def _summarization_node(self, state: PlainLanguageReportAgentState) -> dict[str, Any]:
        plain_language_report = self.summarization_agent.generate_summary(
            medical_report=state["medical_report"],
            extracted_entities=state["extracted_entities"],
        )
        return {"plain_language_report": plain_language_report}


    def _validation_node(self, state: PlainLanguageReportAgentState) -> dict[str, Any]:
        result = self.validation_pipeline.validate_summary(
            medical_report=state["medical_report"],
            extracted_entities=state["extracted_entities"],
            draft_summary=state["plain_language_report"],
            retrieved_definitions=state["retrieved_definitions_dictionary"],
        )
        return {"validation_pipeline_result": result}


    def _refinement_node(self, state: PlainLanguageReportAgentState) -> dict[str, Any]:
        plain_language_report = self.refiner_agent.refine_summary(
            original_report=state["medical_report"],
            extracted_entities=state["extracted_entities"],
            current_summary=state["plain_language_report"],
            validation_report=state["validation_pipeline_result"],
            retrieved_definitions=state["retrieved_definitions_dictionary"],
        )
        return {"plain_language_report": plain_language_report}
