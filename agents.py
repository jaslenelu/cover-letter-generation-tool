from typing import List
from graph import LoRState, VerifiedFact
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Wrapper class for structured output
class FactsList(BaseModel):
    facts: List[VerifiedFact]

class VerificationResult(BaseModel):
    hallucination_risk: str  # "low", "medium", or "high"
    unsupported_sentences: List[str]

def create_agents_with_api_key(api_key: str = None):
    """Create agents with the provided API key"""
    # Use provided API key or fall back to environment variable
    key = api_key or os.getenv("OPENAI_API_KEY")

    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.3,
        api_key=key
    )

    def fact_extraction_agent(state: LoRState) -> LoRState:
        prompt = f"""
        You are extracting ONLY verifiable facts for a recommendation letter.

        Raw materials:
        {state['raw_materials']}

        Extract factual claims with supporting evidence.
        Do NOT infer or exaggerate.
        Return a JSON list of facts with the following structure:
        - claim: the factual claim
        - evidence: supporting evidence from the raw materials
        - confidence: high, medium, or low
        """

        response = llm.with_structured_output(FactsList).invoke(prompt)

        state["verified_facts"] = response.facts
        return state

    def drafting_agent(state: LoRState) -> LoRState:
        facts_text = "\n".join(
            f"- {f.claim} (evidence: {f.evidence}, confidence: {f.confidence})"
            for f in state["verified_facts"]
        )

        prompt = f"""
        You are a {state['recommender_role']} writing a recommendation letter
        for {state['candidate_name']} who is applying to {state['target_program']}.

        IMPORTANT RULES:
        1. You may ONLY use the verified facts listed below
        2. Do NOT add any information not explicitly stated in the facts
        3. Do NOT exaggerate or make inferences beyond what is stated
        4. Write in a formal, professional tone appropriate for an academic recommendation letter
        5. Include proper letter formatting (date, salutation, body, closing)

        Verified facts you can use:
        {facts_text}

        Write a complete, formal recommendation letter that:
        - Opens with your relationship to the candidate
        - Discusses specific achievements and qualities (based only on the facts)
        - Provides concrete examples from the verified facts
        - Concludes with a strong recommendation
        - Maintains a professional and sincere tone throughout

        Format the letter properly with appropriate sections and paragraphs.
        """

        state["draft_letter"] = llm.invoke(prompt).content
        return state

    def verification_agent(state: LoRState) -> LoRState:
        facts_text = "\n".join(
            f"- {f.claim} (evidence: {f.evidence}, confidence: {f.confidence})"
            for f in state["verified_facts"]
        )

        prompt = f"""
        You are verifying a recommendation letter against verified facts.

        Verified facts:
        {facts_text}

        Letter:
        {state['draft_letter']}

        Your task:
        1. Check each sentence in the letter against the verified facts
        2. Identify any sentences that make claims not supported by the facts
        3. Determine the overall hallucination risk level

        Return:
        - hallucination_risk: "low" (if all claims are supported), "medium" (if some minor unsupported claims), or "high" (if major unsupported claims)
        - unsupported_sentences: list of sentences that are not supported by the verified facts
        """

        result = llm.with_structured_output(VerificationResult).invoke(prompt)

        state["hallucination_risk"] = result.hallucination_risk
        state["unsupported_sentences"] = result.unsupported_sentences
        return state

    def decision(state: LoRState) -> str:
        if state["hallucination_risk"] in ["medium", "high"]:
            return "revise"
        return "final"

    return fact_extraction_agent, drafting_agent, verification_agent, decision
