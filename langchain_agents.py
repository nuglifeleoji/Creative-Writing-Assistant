
import os
import json
import asyncio
from typing import Dict, Any

# 确保你已经安装了以下库
# pip install langchain langchain-openai

# 注意配置OPENAI_API_KEY以及graphrag所在路径(代码第172行)

from dotenv import load_dotenv

load_dotenv()

# 优先读取 OPENAI_API_KEY，其次 AZURE_OPENAI_API_KEY，不要把密钥当作环境变量名
api_key =os.getenv("AZURE_OPENAI_API_KEY") or ""

import tiktoken
from langchain.agents import tool
from langchain.agents import create_react_agent, AgentExecutor, create_tool_calling_agent
from langchain import hub
from langchain_openai import ChatOpenAI,AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from search.global_search import global_search as graphrag_global_search
from search.global_search import global_retrieve
from search.local_search import local_search
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import prompt_utils
import prompt
class GraphAnalysisAgent:
    def __init__(self):
        self.global_search = graphrag_global_search
        self.local_search = local_search
    async def global_search_async(self, query: str) -> Dict[str, Any]:
        """直接调用 agent.py 中的 global_search（GraphRAG GlobalSearch），返回精简文本。"""
        try:
            res = await graphrag_global_search(query)
            # agent.py 当前可能返回结果对象或文本，这里统一抽取文本
            text = getattr(res, "response", res)
            if not isinstance(text, str):
                text = str(text)
            return {"method": "global", "query": query, "result": text, "success": True}
        except Exception as e:
            return {"method": "global", "query": query, "error": str(e), "success": False}
    
    async def global_retrieve_async(self, query: str) -> Dict[str, Any]:
        """直接调用 agent.py 中的 global_retrieve（GraphRAG GlobalSearch），返回精简文本。"""
        try:
            res = await global_retrieve(query)

            text = getattr(res, "response", res)
            if not isinstance(text, str):
                text = str(text)
            # current_tokens = 0
            # tokenizer = tiktoken.get_encoding("cl100k_base")
            # selected_text = []
            # for txt in text:
            #     tokens = len(tokenizer.encode(txt))
            #     if current_tokens + tokens > 3000:
            #         break
            #     current_tokens += tokens
            #     selected_text.append(txt)
            # context = "\n".join(selected_text)
            return {"method": "global", "query": query, "result": text, "success": True}
        except Exception as e:
            return {"method": "global", "query": query, "error": str(e), "success": False}

    async def local_search_async(self, query: str) -> Dict[str, Any]:
        try:
            res = await local_search(query)
            # agent.py 当前可能返回结果对象或文本，这里统一抽取文本
            text = getattr(res, "response", res)
            if not isinstance(text, str):
                text = str(text)
            return {"method": "local", "query": query, "result": text, "success": True}
        except Exception as e:
            return {"method": "local", "query": query, "error": str(e), "success": False}

    async def get_characters_async(self) -> Dict[str, Any]:
        return await self.global_search_async("列出故事中的所有人物角色")

    async def get_relationships_async(self, p1: str, p2: str) -> Dict[str, Any]:
        return await self.local_search_async(f"分析{p1}和{p2}之间的关系，包括具体的互动和对话")

    async def get_important_locations_async(self) -> Dict[str, Any]:
        return await self.global_search_async("分析故事中的重要地点和场景")

    async def background_knowledge_async(self) -> Dict[str, Any]:
        return await self.global_search_async("分析故事的背景知识")
    
    async def get_worldview_async(self) -> Dict[str, Any]:
        return await self.global_search_async("获取故事的世界观和基本设定")

    async def get_character_profile_async(self, character_name: str) -> Dict[str, Any]:
        return await self.local_search_async(f"获取{character_name}的详细信息，包括外貌、性格、行为特点和重要对话")
    
    async def get_significant_event_async(self, event_name:str) -> Dict[str, Any]:
        return await self.local_search_async(f"获取事件{event_name}的详细信息，包括具体经过、参与人物和对话")
    
    async def get_main_theme_async(self) -> Dict[str, Any]:
        return await self.global_retrieve_async("分析故事的主题")
    async def mock_coversation_async(self, character1_name: str, character2_name: str) -> Dict[str, Any]:
        return await self.local_search_async(f"模拟{character1_name}和{character2_name}的对话")
    async def get_open_questions_async(self) -> Dict[str, Any]:
        return await self.global_search_async("本书有什么悬念或者没有解决的伏笔？")
    async def get_conflict_async(self) -> Dict[str, Any]:
        return await self.global_search_async("罗列出本书最大的冲突是什么")
    async def get_related_characters_async(self, event: str) -> Dict[str, Any]:
        return await self.local_search_async(f"获取{event}事件的关联人物，包括他们的具体行为和对话")
    async def get_causal_chains_async(self, event: str) -> Dict[str, Any]:
        return await self.local_search_async(f"获取{event}事件的因果链：前置条件→触发→结果→后果")
    async def style_guardrails_async(self, persona: str) -> Dict[str, Any]:
        return await self.global_search_async(f"总结{persona}的叙事风格：允许和禁止的句式、词汇、常见修辞、视角限制、节奏建议，列表输出。")
    async def canon_alignment_async(self, text: str) -> Dict[str, Any]:
        return await self.local_search_async(f"评估以下文本与正史/世界规则的一致性（角色OOC、设定违背、历史违背各给要点评价与依据）：{text[:3000]}")
    async def contradiction_test_async(self, text: str) -> Dict[str, Any]:
        return await self.local_search_async(f"找出以下文本与原著叙述的冲突点（逐条列出冲突、对应原著证据ID/短摘）：{text[:3000]}")
    async def continue_story_async(self, brief: str, persona: str = "保持与原著一致的叙述者口吻与角色对白风格", target_style: str = "紧凑、具象细节、对白推动剧情", words_per_scene: int = 600, max_iters: int = 2) -> Dict[str, Any]:
        return await self.local_search_async(f"为以下大纲续写一个场景（不超过{words_per_scene}词）：{brief[:3000]}")
    async def imagine_conversation_async(self, character1_name: str, character2_name: str) -> Dict[str, Any]:
        return await self.local_search_async(f"想象{character1_name}和{character2_name}的对话")
    async def extract_quotes_async(self, name:str, n:int=8) -> Dict[str, Any]:
        q = f"列出{name}最具代表性的台词{n}条（每条<=40字，附章节/段落编号），严格JSON数组："
        return await self.local_search_async(q)
    async def narrative_pov_async(self) -> Dict[str, Any]:
        q = """
    分析叙事视角与可靠性：POV类型、切换点、可能偏见/误导的证据。用分点列出，每点附<=40字短摘+章节。
    """
        return await self.global_search_async(q)
    async def get_motifs_symbols_async(self, max_items:int=20) -> Dict[str, Any]:
        q = f"""
    抽取意象/母题/象征（最多{max_items}条），严格JSON：
    [{{"motif":"…","meaning":"…","linked_themes":["…"],"chapters":["…"],"evidence":[{{"chapter":"…","quote":"<=40字"}}]}}]
    """
        return await self.local_search_async(q)
    async def build_story_outline_async(self, brief:str, target_style:str="紧凑具象") -> Dict[str, Any]:
        q = f"""
    基于原著约束，为“{brief}”生成三幕式续写大纲（每幕3-5要点），标注涉及人物/地点/冲突/目标。条目式输出。
    风格：{target_style}。严禁违反既有设定。
    """
        return await self.global_search_async(q)
    async def emotion_curve_async(self, scope:str="全书") -> Dict[str, Any]:
        q = f"提取{scope}的情感曲线关键转折（喜/怒/哀/惧/惊/厌/信），列出转折点章节与触发事件，各给<=40字短摘。"
        return await self.global_search_async(q)
    async def compare_characters_async(self, a:str, b:str) -> Dict[str, Any]:
        q = f"""
    比较{a}与{b}，严格JSON：
    {{"values":["…"],"goals":["…"],"methods":["…"],"red_lines":["…"],"decision_style":"冲动|谨慎|算计","evidence":[{{"chapter":"…","quote":"<=40字"}}]}}
    """
        return await self.local_search_async(q)

# --- 第二步：创建 LangChain Agent ---
def create_graphrag_agent(graphrag_agent_instance: GraphAnalysisAgent) -> AgentExecutor:
    """
    创建并返回一个可以调用 GraphRAG 命令行功能的 LangChain Agent。
    """
    # 使用 @tool 装饰器，将 GraphAnalysisAgent 的方法包装成 LangChain 工具
    # 注意：这里的工具函数需要能够被 Agent 直接调用，所以我们使用闭包来传递实例
    @tool
    async def get_characters_tool() -> str:
        """使用 GraphRAG 的全局查询功能获取故事中的所有人物角色。"""
        result = await graphrag_agent_instance.get_characters_async()
        return json.dumps(result, ensure_ascii=False)

    @tool
    async def get_relationships_tool(p1: str, p2: str) -> str:
        """获取两个特定人物之间的关系。输入参数p1和p2是人物名称。如果没有找到两个人物的关系，可以尝试单独查询两个人物的背景信息，并且尝试找到和他们共同相关的人来判断他们之间可能的关系"""
        result = await graphrag_agent_instance.get_relationships_async(p1, p2)
        return json.dumps(result, ensure_ascii=False)

    @tool
    async def get_important_locations_tool() -> str:
        """使用 GraphRAG 的全局查询功能获取故事中的重要地点。"""
        result = await graphrag_agent_instance.get_important_locations_async()
        return json.dumps(result, ensure_ascii=False)

    @tool
    async def background_knowledge_tool() -> str:
        """使用 GraphRAG 的全局查询功能获取故事的背景知识。"""
        result = await graphrag_agent_instance.background_knowledge_async()
        return json.dumps(result, ensure_ascii=False)
    
    @tool
    async def get_worldview_tool() -> str:
        """使用 GraphRAG 的全局查询功能获取故事的世界观和基本设定。"""
        result = await graphrag_agent_instance.get_worldview_async()
        return json.dumps(result, ensure_ascii=False)

    @tool
    async def local_search_tool(query: str) -> str:
        """使用 GraphRAG 的局部查询功能进行自定义搜索。输入是一个字符串形式的查询。"""
        result = await graphrag_agent_instance.local_search_async(query)
        return json.dumps(result, ensure_ascii=False)

    @tool
    async def global_search_tool(query: str) -> str:
        """使用 GraphRAG 的全局查询功能进行自定义搜索。输入是一个字符串形式的查询。"""
        result = await graphrag_agent_instance.global_search_async(query)
        return json.dumps(result, ensure_ascii=False)
    @tool 
    async def get_character_profile_tool(character_name: str) -> str:
        """获取特定人物的详细信息。输入参数character_name是人物名称。"""
        result = await graphrag_agent_instance.get_character_profile_async(character_name)
        return json.dumps(result, ensure_ascii=False)
    @tool
    async def get_significant_event_tool(event_name: str) -> str:
        """获取特定事件的详细信息。输入参数event_name是事件名称。"""
        result = await graphrag_agent_instance.get_significant_event_async(event_name)
        return json.dumps(result, ensure_ascii=False)

    @tool
    async def get_main_theme_tool() -> str:
        """获取故事的主题。"""
        result = await graphrag_agent_instance.get_main_theme_async()
        return json.dumps(result, ensure_ascii=False)
    @tool 
    async def get_open_questions_tool() -> str:
        """获取本书的悬念或者未解决的伏笔。"""
        result = await graphrag_agent_instance.get_open_questions_async()
        return json.dumps(result, ensure_ascii=False)
    @tool
    async def get_causal_chains_tool(event: str) -> str:
        """获取给定事件的因果链。可以知道是什么导致的该事件，然后该事件导致了什么样的结果，最后结果又导致了什么样的后果"""
        result = await graphrag_agent_instance.get_causal_chains_async(event)
        return json.dumps(result, ensure_ascii=False)
    @tool
    async def style_guardrails_tool(persona: str) -> str:
        """产出风格护栏：允许/禁止的句式、词汇、视角、节奏等（供续写遵守）"""
        q = f"总结{persona}的叙事风格：允许和禁止的句式、词汇、常见修辞、视角限制、节奏建议，列表输出。"
        res = await graphrag_agent_instance.global_search_async(q)
        return json.dumps(res, ensure_ascii=False)

    @tool
    async def canon_alignment_tool(text: str) -> str:
        """评估文本与正史/世界规则一致性（角色OOC/设定违背/历史违背），给要点与依据"""
        q = f"评估以下文本与正史/世界规则的一致性（角色OOC、设定违背、历史违背各给要点评价与依据）：{text[:3000]}"
        res = await graphrag_agent_instance.local_search_async(q)
        return json.dumps(res, ensure_ascii=False)

    @tool
    async def contradiction_test_tool(text: str) -> str:
        """检测文本与原著叙述的冲突点，给出原文证据片段定位"""
        q = f"找出以下文本与原著叙述的冲突点（逐条列出冲突、对应原著证据ID/短摘）：{text[:3000]}"
        res = await graphrag_agent_instance.local_search_async(q)
        return json.dumps(res, ensure_ascii=False)
    @tool
    async def get_conflict_tool() -> str:
        """获取本书最大的冲突。"""
        result = await graphrag_agent_instance.get_conflict_async()
        return json.dumps(result, ensure_ascii=False)
    @tool
    async def get_related_characters_tool(event: str) -> str:
        """获取给定事件的关联人物。"""
        result = await graphrag_agent_instance.get_related_characters_async(event)
        return json.dumps(result, ensure_ascii=False)
    @tool
    async def imagine_conversation_tool(character1_name: str, character2_name: str) -> str:
        """想象两个角色之间的对话。"""
        result = await graphrag_agent_instance.imagine_conversation_async(character1_name, character2_name)
        return json.dumps(result, ensure_ascii=False)
    @tool
    async def extract_quotes_tool(name:str, n:int=8) -> str:
        """获取特定人物的台词。"""
        result = await graphrag_agent_instance.extract_quotes_async(name, n)
        return json.dumps(result, ensure_ascii=False)
    @tool
    async def narrative_pov_tool() -> str:
        """获取本书的叙事视角。"""
        result = await graphrag_agent_instance.narrative_pov_async()
        return json.dumps(result, ensure_ascii=False)
    @tool
    async def get_motifs_symbols_tool(max_items:int=20) -> str:
        """获取本书的意象/母题/象征。"""
        result = await graphrag_agent_instance.get_motifs_symbols_async(max_items)
        return json.dumps(result, ensure_ascii=False)
    @tool
    async def build_story_outline_tool(brief:str, target_style:str="紧凑具象") -> str:
        """基于原著约束，为“{brief}”生成三幕式续写大纲（每幕3-5要点），标注涉及人物/地点/冲突/目标。条目式输出。风格：{target_style}。严禁违反既有设定。"""
        result = await graphrag_agent_instance.build_story_outline_async(brief, target_style)
        return json.dumps(result, ensure_ascii=False)
    @tool
    async def emotion_curve_tool(scope:str="全书") -> str:
        """获取本书的情感曲线。"""
        result = await graphrag_agent_instance.emotion_curve_async(scope)
        return json.dumps(result, ensure_ascii=False)
    @tool
    async def compare_characters_tool(a:str, b:str) -> str:
        """比较两个角色。"""
        result = await graphrag_agent_instance.compare_characters_async(a, b)
        return json.dumps(result, ensure_ascii=False)
    
    # @tool
    # async def continue_story_tool(
    #     brief: str,
    #     persona: str = "保持与原著一致的叙述者口吻与角色对白风格",
    #     target_style: str = "紧凑、具象细节、对白推动剧情",
    #     words_per_scene: int = 600,
    #     max_iters: int = 2
    # ) -> str:
    #     """
    #     一键续写：大纲->节拍->写作->一致性与冲突检查->必要时修订。返回最终场景文本和校验信息。
    #     - brief: 用户的续写意图说明
    #     - persona: 人设与口吻约束
    #     - target_style: 文风目标
    #     """
    #     # 1) 取风格护栏与世界规则
    #     guard = await graphrag_agent_instance.global_search_async(
    #         f"总结{persona}的叙事风格：允许/禁止的句式、常见修辞、视角限制、节奏建议，列表输出。"
    #     )
    #     world = await graphrag_agent_instance.global_search_async(
    #         "总结世界观硬性规则（政治/法律/科技/宗教/魔法/经济），违反的后果，列表输出。"
    #     )

    #     # 2) 基于原著生成续写大纲与节拍（用 GraphRAG 保守抽纲）
    #     outline = await graphrag_agent_instance.global_search_async(
    #         f"基于原著信息，按照三幕式生成续写大纲（每幕3-5要点，标注涉及人物/地点/冲突/目标）；风格：{target_style}；用户意图：{brief}"
    #     )
    #     beats = await graphrag_agent_instance.global_search_async(
    #         f"把以下大纲拆为节拍表（每节拍含：目的、冲突、转折、关键信息、涉及角色、证据需求），用紧凑清单：\n{outline.get('result','')[:2800]}"
    #     )
    #     # 选第一条节拍写一个场景（需要更多可拆循环）
    #     beat_first = "\n".join(beats.get("result","").split("\n")[:10])
    #     # 2) 基于原著生成续写大纲与节拍（用 GraphRAG 保守抽纲）
    #     outline = await graphrag_agent_instance.global_search_async(
    #         f"基于原著信息，按照三幕式生成续写大纲（每幕3-5要点，标注涉及人物/地点/冲突/目标）；风格：{target_style}；用户意图：{brief}"
    #     )
    #     beats = await graphrag_agent_instance.global_search_async(
    #         f"把以下大纲拆为节拍表（每节拍含：目的、冲突、转折、关键信息、涉及角色、证据需求），用紧凑清单：\n{outline.get('result','')[:2800]}"
    #     )
    #     # 选第一条节拍写一个场景（需要更多可拆循环）
    #     beat_first = "\n".join(beats.get("result","").split("\n")[:10])

    #     # 3) 写场景（用生成型 LLM）
    #     sys = SystemMessage(content=(
    #         "你是一名严谨的续写作者，必须遵守原著世界规则与角色性格。"
    #         "生成文本要可直接发布，避免方向性描述。"
    #         f"【风格护栏】{guard.get('result','')}\n【世界规则】{world.get('result','')}"
    #     ))
    #     user = HumanMessage(content=(
    #         f"请写一个完整场景（不超过{words_per_scene}词）。"
    #         f"要求：遵守人物口吻与设定、用对白推动剧情、细节具象、避免与原著冲突。\n"
    #         f"【节拍】\n{beat_first}\n\n【用户意图】\n{brief}"
    #     ))
    #     gen = await llm_gen.ainvoke([sys, user])
    #     scene = gen.content if hasattr(gen, "content") else str(gen)
    #     # 3) 写场景（用生成型 LLM）
    #     sys = SystemMessage(content=(
    #         "你是一名严谨的续写作者，必须遵守原著世界规则与角色性格。"
    #         "生成文本要可直接发布，避免方向性描述。"
    #         f"【风格护栏】{guard.get('result','')}\n【世界规则】{world.get('result','')}"
    #     ))
    #     user = HumanMessage(content=(
    #         f"请写一个完整场景（不超过{words_per_scene}词）。"
    #         f"要求：遵守人物口吻与设定、用对白推动剧情、细节具象、避免与原著冲突。\n"
    #         f"【节拍】\n{beat_first}\n\n【用户意图】\n{brief}"
    #     ))
    #     gen = await llm_gen.ainvoke([sys, user])
    #     scene = gen.content if hasattr(gen, "content") else str(gen)

    #     # 4) 校验 & 可能修订（最多 max_iters 轮）
    #     issues = []
    #     for _ in range(max_iters+1):
    #         # 一致性与冲突检查（用 GraphRAG 做证据对齐）
    #         canon = await graphrag_agent_instance.local_search_async(
    #             f"评估文本与正史/世界规则一致性（角色OOC/设定违背/历史违背各给要点与依据）：{scene[:3000]}"
    #         )
    #         contra = await graphrag_agent_instance.local_search_async(
    #             f"找出文本与原著叙述的冲突点（逐条列出冲突、对应原著证据ID/短摘）：{scene[:3000]}"
    #         )
    #         hard_fail = ("违背" in canon.get("result","")) or ("冲突" in contra.get("result",""))
    #     # 4) 校验 & 可能修订（最多 max_iters 轮）
    #     issues = []
    #     for _ in range(max_iters+1):
    #         # 一致性与冲突检查（用 GraphRAG 做证据对齐）
    #         canon = await graphrag_agent_instance.local_search_async(
    #             f"评估文本与正史/世界规则一致性（角色OOC/设定违背/历史违背各给要点与依据）：{scene[:3000]}"
    #         )
    #         contra = await graphrag_agent_instance.local_search_async(
    #             f"找出文本与原著叙述的冲突点（逐条列出冲突、对应原著证据ID/短摘）：{scene[:3000]}"
    #         )
    #         hard_fail = ("违背" in canon.get("result","")) or ("冲突" in contra.get("result",""))

    #         if not hard_fail:
    #             # 收集关键断言证据（可选）
    #             ev = await graphrag_agent_instance.local_search_async(
    #                 "为上述续写中关键设定与角色动机找出最有力的证据片段（列章节/段落ID+短摘），最多5条。"
    #             )
    #             return json.dumps({
    #                 "status": "DONE",
    #                 "outline": outline,
    #                 "beats": beats,
    #                 "final_text": scene,
    #                 "evidence": ev,
    #                 "issues": issues
    #             }, ensure_ascii=False)
    #         if not hard_fail:
    #             # 收集关键断言证据（可选）
    #             ev = await graphrag_agent_instance.local_search_async(
    #                 "为上述续写中关键设定与角色动机找出最有力的证据片段（列章节/段落ID+短摘），最多5条。"
    #             )
    #             return json.dumps({
    #                 "status": "DONE",
    #                 "outline": outline,
    #                 "beats": beats,
    #                 "final_text": scene,
    #                 "evidence": ev,
    #                 "issues": issues
    #             }, ensure_ascii=False)

    #         issues.append({"canon": canon.get("result",""), "conflict": contra.get("result","")})
    #         issues.append({"canon": canon.get("result",""), "conflict": contra.get("result","")})

    #         # 5) 修订指令（再喂回生成 LLM）
    #         sys2 = SystemMessage(content=(
    #             "根据评审意见修订文本，务必消除OOC与设定/历史冲突，保留节拍目标与风格护栏。"
    #             f"【风格护栏】{guard.get('result','')}\n【评审】{json.dumps(issues[-1], ensure_ascii=False)[:1500]}"
    #         ))
    #         user2 = HumanMessage(content=(
    #             f"请在不超过{words_per_scene}词内重写该场景：\n{scene[:2000]}"
    #         ))
    #         rev = await llm_gen.ainvoke([sys2, user2])
    #         scene = rev.content if hasattr(rev, "content") else str(rev)
    #         # 5) 修订指令（再喂回生成 LLM）
    #         sys2 = SystemMessage(content=(
    #             "根据评审意见修订文本，务必消除OOC与设定/历史冲突，保留节拍目标与风格护栏。"
    #             f"【风格护栏】{guard.get('result','')}\n【评审】{json.dumps(issues[-1], ensure_ascii=False)[:1500]}"
    #         ))
    #         user2 = HumanMessage(content=(
    #             f"请在不超过{words_per_scene}词内重写该场景：\n{scene[:2000]}"
    #         ))
    #         rev = await llm_gen.ainvoke([sys2, user2])
    #         scene = rev.content if hasattr(rev, "content") else str(rev)

    #     # 达到迭代上限仍有问题
    #     return json.dumps({
    #         "status": "BUDGET_EXCEEDED",
    #         "outline": outline,
    #         "beats": beats,
    #         "final_text": scene,
    #         "issues": issues
    #     }, ensure_ascii=False)
    #     # 达到迭代上限仍有问题
    #     return json.dumps({
    #         "status": "BUDGET_EXCEEDED",
    #         "outline": outline,
    #         "beats": beats,
    #         "final_text": scene,
    #         "issues": issues
    #     }, ensure_ascii=False)
    tools = [
        get_characters_tool,
        get_relationships_tool,
        get_important_locations_tool,
        get_significant_event_tool,
        background_knowledge_tool,
        get_worldview_tool,
        local_search_tool,
        global_search_tool,
        get_character_profile_tool,
        get_main_theme_tool,
        get_open_questions_tool,
        get_causal_chains_tool,
        style_guardrails_tool,
        canon_alignment_tool,
        contradiction_test_tool,
        get_conflict_tool,
        get_related_characters_tool,
        imagine_conversation_tool,
        extract_quotes_tool,
        narrative_pov_tool,
        get_motifs_symbols_tool, 
        build_story_outline_tool,
        emotion_curve_tool,
        compare_characters_tool,
        # continue_story_tool
    ]

    # 初始化 LLM
    # 确保你已经设置了 OPENAI_API_KEY 环境变量
    llm = AzureChatOpenAI(
        openai_api_version="2024-12-01-preview",
        azure_deployment="gpt-4o",
        model_name="gpt-4o",
        azure_endpoint="https://tcamp.openai.azure.com/",
        openai_api_key=api_key,
        temperature=0.3,
        streaming=True,
        callbacks=[StreamingStdOutCallbackHandler()]
    )
    llm_gen = AzureChatOpenAI(
        openai_api_version="2024-12-01-preview",
        azure_deployment="gpt-4o",
        model_name="gpt-4o",
        azure_endpoint="https://tcamp.openai.azure.com/",
        openai_api_key=api_key,
        temperature=0.85,   # 更高创造性
        max_tokens=1400     # 续写长度预算（按需调）
    )


    prompt = f"""
    You are a helpful assistant that can answer questions about the data in the tables provided. Your tasks mainly consist of two parts: 1. extract and summarize the information about the book; 2. derivative work based on the book.

    ---Goal---
你是一个智能创作助手，可以进行信息分析和探索，通过系统性的调查来完成复杂的创作任务。
## 历史对话
{{history}}
## 用户问题
{{input}}
## 调查周期 (Investigation Cycle)
你按照一个持续的周期运作：
1. 从多个维度理解用户诉求，拆解用户问题，明确用户意图
2. 根据历史对话，整合有用信息以理解任务目标
3. 根据已掌握的线索和信息缺口，避免和历史对话中完全相同的工具调用（工具参数一致），选择优先级最高的工具，决定接下来要调用哪个工具
4. 当你认为没完成任务时或现有信息无法回答用户问题时，"status_update" 为 "IN_PROGRES"，此时你必须选择一个工具。
5. 当你认为历史对话的信息足够你回答用户问题时，"status_update" 为 "DONE"
## 可用工具 (Available Tools)
{{functions}}
## 工具使用准则 (Tool Usage Guidelines)
{{guidelines}}
## 注意事项
{{requirements}}
响应格式 (Response Format)
{{response_format}}
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", prompt),
        ("user", "{input}\n\n{agent_scratchpad}"),
    ])

    # 创建 Agent
    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)

    # 创建 Agent 执行器
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

# --- 主程序入口 ---
async def main() -> None:
    graph_agent = GraphAnalysisAgent()

    # 使用这个实例创建 LangChain Agent
    agent_executor = create_graphrag_agent(graph_agent)

    print("LangChain Agent with GraphRAG (Python API) tools is ready. Type 'exit' to quit.")

    history = []

    while True:
        user_query = input("\n请输入你的问题：")
        history.append({"role": "user", "content": user_query})
        recent_history = history[-4:]  # 只保留最近的4条历史记录
        history_text = ""
        for msg in recent_history:
            prefix = "用户：" if msg["role"] == "user" else "助手："
            history_text += f"{prefix}{msg['content']}\n"
        if user_query.lower() == 'exit':
            break

        try:
            # 使用异步调用，匹配异步工具
            # response = await agent_executor.ainvoke({"input": user_query, "guidelines": prompt_utils.build_guidelines(), "functions": agent_executor.tools, "requirements": prompt_utils.build_requirements(), "response_format": prompt_utils.build_response_format()})
            response = await agent_executor.ainvoke({"input": user_query, "guidelines": prompt.build_guidelines(), "functions": agent_executor.tools, "requirements": prompt.build_requirements(), "response_format": prompt.build_response_format(), "history": history_text})
            # print("\n--- Agent 回答 ---")
            # print(response.get("output"))
            # print("--------------------\n")
            # history.append({"role": "assistant", "content": response.get("output")})
        except Exception as e:
            print(f"发生错误：{e}")
            break


if __name__ == "__main__":
    asyncio.run(main())

