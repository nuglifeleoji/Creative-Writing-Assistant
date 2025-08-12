import os
from typing import Optional
from dotenv import load_dotenv

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


load_dotenv("./.env")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY") or ""


class PolishAgent:
    """A lightweight agent for polishing and critiquing text.
    - No GraphRAG; uses only LLM with streaming enabled
    - Accepts user draft and optional chat history
    """

    def __init__(
        self,
        azure_endpoint: str = "https://tcamp.openai.azure.com/",
        deployment: str = "gpt-4.1",
        model_name: str = "gpt-4.1",
        api_key: Optional[str] = None,
    ) -> None:
        self.llm_polish = AzureChatOpenAI(
            openai_api_version="2025-01-01-preview",
            azure_deployment=deployment,
            model_name=model_name,
            azure_endpoint=azure_endpoint,
            openai_api_key=api_key or API_KEY,
            temperature=0.2,
            max_tokens=2000,
            streaming=True,
        )

    async def polish_async(
        self,
        draft: str,
        chat_history_text: str = "",
        user_prompt: str = "",
        tone: str = "neutral",
        target_length: str = "original",
    ) -> str:
        system_rules = (
            "你是一个中文写作润色助手，提升清晰度、结构性与一致性，不改变事实与核心含义。\n"
            "- 修正语法/用词/标点/格式\n"
            "- 优化逻辑与段落衔接\n"
            "- 提升可读性与专业性，避免冗余\n"
            "- 保留关键信息与术语，不编造内容\n"
            f"- 目标语气: {tone}；长度策略: {target_length}"
        )

        history_part = f"\n\n[对话历史]\n{chat_history_text}" if chat_history_text else ""
        requirement_part = f"\n\n[用户需求（必须严格满足）]\n{user_prompt}" if user_prompt else ""
        prompt = (
            "请先对照[用户需求]检查草稿是否完全符合要求（题材、风格、结构、长度、禁忌等）。若存在不符合或遗漏，请在润色时一并修正；否则在保持含义不变的前提下优化表达。\n"
            "仅输出润色后的最终文本，不要输出解释或打分。\n\n"
            f"[草稿]\n{draft}{history_part}{requirement_part}"
        )

        messages = [
            SystemMessage(content=system_rules),
            HumanMessage(content=prompt),
        ]

        response = await self.llm_polish.ainvoke(messages)
        return response.content if hasattr(response, "content") else str(response)

    async def critique_async(
        self,
        text: str,
        chat_history_text: str = "",
        criteria: str = "清晰度, 结构性, 语气一致性, 事实保真, 与用户需求一致",
    ) -> str:
        system_rules = (
            "你是一个严谨的中文文本点评助手。\n"
            "- 从清晰度、结构性、语气一致性、事实保真、与用户需求一致性等维度评估\n"
            "- 指出具体可改进之处，并给出简短修改建议\n"
            "- 不编造内容，不加入无根据的信息"
        )

        history_part = f"\n\n[对话历史]\n{chat_history_text}" if chat_history_text else ""
        prompt = (
            "请根据以下标准对文本给出专业点评，并给出改进建议要点：\n"
            f"[点评标准]\n{criteria}\n\n"
            f"[文本]\n{text}{history_part}"
        )

        messages = [
            SystemMessage(content=system_rules),
            HumanMessage(content=prompt),
        ]

        response = await self.llm_polish.ainvoke(messages)
        return response.content if hasattr(response, "content") else str(response)


def create_polish_agent() -> PolishAgent:
    return PolishAgent()


