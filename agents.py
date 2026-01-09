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

def create_agents_with_api_key(api_key: str = None, language: str = "English"):
    """Create agents with the provided API key and language"""
    # Use provided API key or fall back to environment variable
    key = api_key or os.getenv("OPENAI_API_KEY")

    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.3,
        api_key=key
    )

    def fact_extraction_agent(state: LoRState) -> LoRState:
        if language == "English":
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
        else:  # 繁體中文
            prompt = f"""
            您正在為推薦信提取可驗證的事實。

            原始資料：
            {state['raw_materials']}

            提取事實性聲明及其支持證據。
            不要推斷或誇大。
            請以以下結構返回 JSON 事實列表：
            - claim: 事實性聲明
            - evidence: 來自原始資料的支持證據
            - confidence: high（高）、medium（中）或 low（低）
            """

        response = llm.with_structured_output(FactsList).invoke(prompt)

        state["verified_facts"] = response.facts
        return state

    def drafting_agent(state: LoRState) -> LoRState:
        facts_text = "\n".join(
            f"- {f.claim} (evidence: {f.evidence}, confidence: {f.confidence})"
            for f in state["verified_facts"]
        )

        if language == "English":
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
        else:  # 繁體中文
            prompt = f"""
            您是一位{state['recommender_role']}，正在為{state['candidate_name']}撰寫推薦信，
            該候選人正在申請{state['target_program']}。

            重要規則：
            1. 您只能使用以下列出的已驗證事實
            2. 不要添加任何未在事實中明確說明的資訊
            3. 不要誇大或做出超出所述內容的推論
            4. 使用適合學術推薦信的正式、專業語氣
            5. 包含適當的信件格式（日期、稱呼、正文、結語）

            您可以使用的已驗證事實：
            {facts_text}

            請撰寫一封完整、正式的推薦信，包含：
            - 開頭說明您與候選人的關係
            - 討論具體成就和品質（僅基於事實）
            - 從已驗證的事實中提供具體例子
            - 以強烈的推薦作為結尾
            - 始終保持專業和真誠的語氣

            請以適當的段落正確格式化信件。請用臺灣繁體中文撰寫整封推薦信。
            """

        state["draft_letter"] = llm.invoke(prompt).content
        return state

    def verification_agent(state: LoRState) -> LoRState:
        facts_text = "\n".join(
            f"- {f.claim} (evidence: {f.evidence}, confidence: {f.confidence})"
            for f in state["verified_facts"]
        )

        if language == "English":
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
        else:  # 繁體中文
            prompt = f"""
            您正在對照已驗證的事實來驗證推薦信。

            已驗證的事實：
            {facts_text}

            推薦信：
            {state['draft_letter']}

            您的任務：
            1. 將信中的每個句子與已驗證的事實進行對照
            2. 識別任何未被事實支持的聲明句子
            3. 確定整體的幻覺風險等級

            返回：
            - hallucination_risk: "low"（如果所有聲明都有支持）、"medium"（如果有一些小的不支持的聲明）或 "high"（如果有重大的不支持的聲明）
            - unsupported_sentences: 未被已驗證事實支持的句子列表
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
