from typing import List, Optional, TypedDict
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END

class VerifiedFact(BaseModel):
    claim: str
    evidence: str
    confidence: str  # high, medium, low

class LoRState(TypedDict):
    candidate_name: str
    recommender_role: str  # "Professor", "Manager"
    target_program: str

    raw_materials: str  # CV, notes, bullets
    verified_facts: List[VerifiedFact]

    draft_letter: Optional[str]

    hallucination_risk: Optional[str]  # low, medium, high
    unsupported_sentences: Optional[List[str]]

def build_graph(api_key: str = None):
    """Build and return the LangGraph workflow for recommendation letter generation"""
    # Import here to avoid circular dependency
    from agents import create_agents_with_api_key

    # Create agents with the provided API key
    fact_extraction_agent, drafting_agent, verification_agent, decision = create_agents_with_api_key(api_key)

    graph = StateGraph(LoRState)

    graph.add_node("fact_extraction", fact_extraction_agent)
    graph.add_node("draft", drafting_agent)
    graph.add_node("verify", verification_agent)

    graph.set_entry_point("fact_extraction")

    graph.add_edge("fact_extraction", "draft")
    graph.add_edge("draft", "verify")

    graph.add_conditional_edges(
        "verify",
        decision,
        {
            "revise": "draft",
            "final": END
        }
    )

    return graph.compile()

# For backward compatibility
lor_graph = None  # Will be created when build_graph() is called
