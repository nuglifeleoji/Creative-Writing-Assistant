import os
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_agent import GraphAnalysisAgent, create_graphrag_agent
from search.rag_engine import multi_book_manager


load_dotenv("./.env")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY") or ""


class CrossLangChainAgent:
    """Cross-book composition helper.
    - Does not change global currentBook
    - Collects contexts from multiple books in parallel
    - Prepares a single generation prompt that fuses constraints
    """

    def __init__(
        self,
        azure_endpoint: str = "https://tcamp.openai.azure.com/",
        deployment: str = "gpt-4.1",
        model_name: str = "gpt-4.1",
        api_key: Optional[str] = None,
    ) -> None:
        self.llm_gen = AzureChatOpenAI(
            openai_api_version="2025-01-01-preview",
            azure_deployment=deployment,
            model_name=model_name,
            azure_endpoint=azure_endpoint,
            openai_api_key=api_key or API_KEY,
            temperature=0.6,
            max_tokens=2000,
            streaming=True,
        )

    async def _retrieve_for_book(
        self,
        book_name: str,
        prompt: str,
        mode: str = "both",
        topk: int = 5,
    ) -> Dict[str, Any]:
        engine = multi_book_manager.engines.get(book_name)
        if engine is None:
            return {
                "book": book_name,
                "success": False,
                "error": f"书本未加载: {book_name}",
            }
        results: List[Tuple[str, Dict[str, Any]]] = []
        try:
            tasks = []
            if mode in ("global", "both"):
                tasks.append(engine.global_search_retrieve(prompt))
            if mode in ("local", "both"):
                tasks.append(engine.local_search_retrieve(prompt))
            gathered = await asyncio.gather(*tasks, return_exceptions=True)
            for r in gathered:
                if isinstance(r, Exception):
                    continue
                if isinstance(r, dict):
                    results.append((r.get("method", "unknown"), r))
        except Exception as e:
            return {"book": book_name, "success": False, "error": str(e)}

        # Build brief context
        contexts: List[str] = []
        for _, r in results:
            ctx = r.get("retrieved_context", {})
            summary = ctx.get("context_summary")
            if summary:
                contexts.append(summary)
            else:
                full_text = ctx.get("full_text") or ""
                if isinstance(full_text, str) and full_text:
                    contexts.append(full_text[:1200])

        # Reduce size
        merged = "\n\n".join(contexts[:topk])
        return {
            "book": book_name,
            "success": True,
            "context": merged,
        }

    async def build_contexts(
        self, books: List[str], prompt: str, mode: str = "both", topk: int = 5
    ) -> List[Dict[str, Any]]:
        tasks = [self._retrieve_for_book(b, prompt, mode, topk) for b in books]
        return await asyncio.gather(*tasks)

    def build_messages(
        self, contexts: List[Dict[str, Any]], user_prompt: str
    ) -> List[Any]:
        # Construct a strict composition instruction to avoid contradictions
        sys = (
            "你是一个跨书创作助手。你需要融合多本书的人设/世界观/语体，"
            "在不违背各自原著设定的前提下进行创作。严格避免编造原著未给出的事实。"
        )
        ctx_lines = []
        for item in contexts:
            if not item.get("success"):
                ctx_lines.append(f"【{item.get('book')}: 检索失败或未加载】{item.get('error','')}\n")
                continue
            context = item.get("context", "")
            ctx_lines.append(f"【{item.get('book')} 摘要】\n{context}\n")
        ctx_block = "\n".join(ctx_lines)

        user = (
            "请基于以下多书上下文进行创作。\n"
            "[多书上下文]\n" + ctx_block + "\n"
            "[用户创作需求]\n" + user_prompt + "\n\n"
            "创作要求：\n"
            "- 保持各自角色语言风格与行为逻辑\n"
            "- 严格遵守设定与世界规则\n"
            "- 如存在冲突，以各书原著设定为准，尽量协调\n"
            "- 内容连贯、完整，避免空泛\n"
        )
        return [SystemMessage(content=sys), HumanMessage(content=user)]


class CrossOrchestrator:
    """Run per-book temporary sub agents using original tool chain, emitting tool events."""
    def __init__(self, sse_emit):
        # sse_emit(event_type: str, payload: dict) -> None
        self.sse_emit = sse_emit

    async def _run_one_book_agent(
        self,
        book_name: str,
        prompt: str,
        history: List[str],
        callback_handler_factory,
    ) -> Dict[str, Any]:
        try:
            engine = multi_book_manager.engines.get(book_name)
            if engine is None:
                return {"book": book_name, "success": False, "error": f"书本未加载: {book_name}"}

            # 临时子代理，不修改全局 currentBook
            sub_agent = GraphAnalysisAgent(use_multi_book=True)
            sub_agent.rag_engine = multi_book_manager
            sub_agent.current_engine = engine

            agent_executor = create_graphrag_agent(sub_agent)

            # 新的回调实例（会直接推送SSE）
            handler = callback_handler_factory()

            # 执行一次完整链路（让工具事件与单书一致）
            resp = await agent_executor.ainvoke(
                {"input": prompt, "chat_history": history},
                config={"callbacks": [handler]}
            )

            # 解析结果
            if isinstance(resp, dict):
                output = resp.get("output", "")
                steps = resp.get("intermediate_steps", [])
            else:
                output = str(resp)
                steps = []

            # 产出 per_book_context（预览）事件
            self.sse_emit("per_book_context", {
                "book": book_name,
                "success": True,
                "preview": output[:200]
            })

            return {"book": book_name, "success": True, "context": output, "steps": len(steps)}
        except Exception as e:
            self.sse_emit("per_book_context", {
                "book": book_name,
                "success": False,
                "preview": f"error: {e}"
            })
            return {"book": book_name, "success": False, "error": str(e)}

    async def run_per_book_agents(
        self,
        books: List[str],
        prompt: str,
        history: List[str],
        callback_handler_factory,
    ) -> List[Dict[str, Any]]:
        tasks = [
            self._run_one_book_agent(b, prompt, history, callback_handler_factory)
            for b in books
        ]
        return await asyncio.gather(*tasks)


def create_cross_langchain_agent() -> CrossLangChainAgent:
    return CrossLangChainAgent()


