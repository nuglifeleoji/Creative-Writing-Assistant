
# import os
# import json
# import asyncio
# from typing import Dict, Any

# # 确保你已经安装了以下库
# # pip install langchain langchain-openai

# # 注意配置OPENAI_API_KEY以及graphrag所在路径(代码第172行)

# from dotenv import load_dotenv

# load_dotenv()

# # 优先读取 OPENAI_API_KEY，其次 AZURE_OPENAI_API_KEY，不要把密钥当作环境变量名
# api_key =os.getenv("AZURE_OPENAI_API_KEY") or ""

# import tiktoken
# from langchain.agents import tool
# from langchain.agents import create_react_agent, AgentExecutor, create_tool_calling_agent
# from langchain import hub
# from langchain_openai import ChatOpenAI,AzureChatOpenAI
# from langchain.prompts import ChatPromptTemplate
# from langchain_core.messages import SystemMessage, HumanMessage
# from search.global_search import global_search as graphrag_global_search
# from search.global_search import global_retrieve
# from search.local_search import local_search
# from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
# import prompt_utils
# import prompt
# class GraphAnalysisAgent:
#     def __init__(self):
#         self.global_search = graphrag_global_search
#         self.local_search = local_search
#     async def global_search_async(self, query: str) -> Dict[str, Any]:
#         """直接调用 agent.py 中的 global_search（GraphRAG GlobalSearch），返回精简文本。"""
#         try:
#             res = await graphrag_global_search(query)
#             # agent.py 当前可能返回结果对象或文本，这里统一抽取文本
#             text = getattr(res, "response", res)
#             if not isinstance(text, str):
#                 text = str(text)
#             return {"method": "global", "query": query, "result": text, "success": True}
#         except Exception as e:
#             return {"method": "global", "query": query, "error": str(e), "success": False}
    
#     async def global_retrieve_async(self, query: str) -> Dict[str, Any]:
#         """直接调用 agent.py 中的 global_retrieve（GraphRAG GlobalSearch），返回精简文本。"""
#         try:
#             res = await global_retrieve(query)

#             text = getattr(res, "response", res)
#             if not isinstance(text, str):
#                 text = str(text)
#             # current_tokens = 0
#             # tokenizer = tiktoken.get_encoding("cl100k_base")
#             # selected_text = []
#             # for txt in text:
#             #     tokens = len(tokenizer.encode(txt))
#             #     if current_tokens + tokens > 3000:
#             #         break
#             #     current_tokens += tokens
#             #     selected_text.append(txt)
#             # context = "\n".join(selected_text)
#             return {"method": "global", "query": query, "result": text, "success": True}
#         except Exception as e:
#             return {"method": "global", "query": query, "error": str(e), "success": False}

#     async def local_search_async(self, query: str) -> Dict[str, Any]:
#         try:
#             res = await local_search(query)
#             # agent.py 当前可能返回结果对象或文本，这里统一抽取文本
#             text = getattr(res, "response", res)
#             if not isinstance(text, str):
#                 text = str(text)
#             return {"method": "local", "query": query, "result": text, "success": True}
#         except Exception as e:
#             return {"method": "local", "query": query, "error": str(e), "success": False}

#     async def get_characters_async(self) -> Dict[str, Any]:
#         return await self.global_search_async("列出故事中的所有人物角色")

#     async def get_relationships_async(self, p1: str, p2: str) -> Dict[str, Any]:
#         return await self.global_search_async(f"分析{p1}和{p2}之间的关系")

#     async def get_important_locations_async(self) -> Dict[str, Any]:
#         return await self.global_search_async("分析故事中的重要地点和场景")

#     async def background_knowledge_async(self) -> Dict[str, Any]:
#         return await self.global_search_async("分析故事的背景知识")
    
#     async def get_worldview_async(self) -> Dict[str, Any]:
#         return await self.global_search_async("获取故事的世界观和基本设定")

#     async def get_character_profile_async(self, character_name: str) -> Dict[str, Any]:
#         return await self.global_search_async(f"获取{character_name}的详细信息")
    
#     async def get_significant_event_async(self, event_name:str) -> Dict[str, Any]:
#         return await self.global_search_async(f"获取事件{event_name}的详细信息")
    
#     async def get_main_theme_async(self) -> Dict[str, Any]:
#         return await self.global_retrieve_async("分析故事的主题")
#     async def mock_coversation_async(self, character1_name: str, character2_name: str) -> Dict[str, Any]:
#         return await self.local_search_async(f"模拟{character1_name}和{character2_name}的对话")
#     async def get_open_questions_async(self) -> Dict[str, Any]:
#         return await self.global_search_async("本书有什么悬念或者没有解决的伏笔？")
#     async def get_conflict_async(self) -> Dict[str, Any]:
#         return await self.global_search_async("罗列出本书最大的冲突是什么")
#     async def get_related_characters_async(self, event: str) -> Dict[str, Any]:
#         return await self.global_search_async(f"获取{event}事件的关联人物")
#     async def get_causal_chains_async(self, event: str) -> Dict[str, Any]:
#         return await self.local_search_async(f"获取{event}事件的因果链：前置条件→触发→结果→后果")
#     async def style_guardrails_async(self, persona: str) -> Dict[str, Any]:
#         return await self.global_search_async(f"总结{persona}的叙事风格：允许和禁止的句式、词汇、常见修辞、视角限制、节奏建议，列表输出。")
#     async def canon_alignment_async(self, text: str) -> Dict[str, Any]:
#         return await self.local_search_async(f"评估以下文本与正史/世界规则的一致性（角色OOC、设定违背、历史违背各给要点评价与依据）：{text[:3000]}")
#     async def contradiction_test_async(self, text: str) -> Dict[str, Any]:
#         return await self.local_search_async(f"找出以下文本与原著叙述的冲突点（逐条列出冲突、对应原著证据ID/短摘）：{text[:3000]}")
#     async def continue_story_async(self, brief: str, persona: str = "保持与原著一致的叙述者口吻与角色对白风格", target_style: str = "紧凑、具象细节、对白推动剧情", words_per_scene: int = 600, max_iters: int = 2) -> Dict[str, Any]:
#         return await self.local_search_async(f"为以下大纲续写一个场景（不超过{words_per_scene}词）：{brief[:3000]}")
#     async def imagine_conversation_async(self, character1_name: str, character2_name: str) -> Dict[str, Any]:
#         return await self.local_search_async(f"想象{character1_name}和{character2_name}的对话")
#     async def extract_quotes_async(self, name:str, n:int=8) -> Dict[str, Any]:
#         q = f"列出{name}最具代表性的台词{n}条（每条<=40字，附章节/段落编号），严格JSON数组："
#         return await self.local_search_async(q)
#     async def narrative_pov_async(self) -> Dict[str, Any]:
#         q = """
#     分析叙事视角与可靠性：POV类型、切换点、可能偏见/误导的证据。用分点列出，每点附<=40字短摘+章节。
#     """
#         return await self.global_search_async(q)
#     async def get_motifs_symbols_async(self, max_items:int=20) -> Dict[str, Any]:
#         q = f"""
#     抽取意象/母题/象征（最多{max_items}条），严格JSON：
#     [{{"motif":"…","meaning":"…","linked_themes":["…"],"chapters":["…"],"evidence":[{{"chapter":"…","quote":"<=40字"}}]}}]
#     """
#         return await self.local_search_async(q)
#     async def build_story_outline_async(self, brief:str, target_style:str="紧凑具象") -> Dict[str, Any]:
#         q = f"""
#     基于原著约束，为“{brief}”生成三幕式续写大纲（每幕3-5要点），标注涉及人物/地点/冲突/目标。条目式输出。
#     风格：{target_style}。严禁违反既有设定。
#     """
#         return await self.global_search_async(q)
#     async def emotion_curve_async(self, scope:str="全书") -> Dict[str, Any]:
#         q = f"提取{scope}的情感曲线关键转折（喜/怒/哀/惧/惊/厌/信），列出转折点章节与触发事件，各给<=40字短摘。"
#         return await self.global_search_async(q)
#     async def compare_characters_async(self, a:str, b:str) -> Dict[str, Any]:
#         q = f"""
#     比较{a}与{b}，严格JSON：
#     {{"values":["…"],"goals":["…"],"methods":["…"],"red_lines":["…"],"decision_style":"冲动|谨慎|算计","evidence":[{{"chapter":"…","quote":"<=40字"}}]}}
#     """
#         return await self.global_search_async(q)

# # --- 第二步：创建 LangChain Agent ---
# def create_graphrag_agent(graphrag_agent_instance: GraphAnalysisAgent) -> AgentExecutor:
#     """
#     创建并返回一个可以调用 GraphRAG 命令行功能的 LangChain Agent。
#     """
#     # 使用 @tool 装饰器，将 GraphAnalysisAgent 的方法包装成 LangChain 工具
#     # 注意：这里的工具函数需要能够被 Agent 直接调用，所以我们使用闭包来传递实例
#     @tool
#     async def get_characters_tool() -> str:
#         """使用 GraphRAG 的全局查询功能获取故事中的所有人物角色。"""
#         result = await graphrag_agent_instance.get_characters_async()
#         return json.dumps(result, ensure_ascii=False)

#     @tool
#     async def get_relationships_tool(p1: str, p2: str) -> str:
#         """获取两个特定人物之间的关系。输入参数p1和p2是人物名称。如果没有找到两个人物的关系，可以尝试单独查询两个人物的背景信息，并且尝试找到和他们共同相关的人来判断他们之间可能的关系"""
#         result = await graphrag_agent_instance.get_relationships_async(p1, p2)
#         return json.dumps(result, ensure_ascii=False)

#     @tool
#     async def get_important_locations_tool() -> str:
#         """使用 GraphRAG 的全局查询功能获取故事中的重要地点。"""
#         result = await graphrag_agent_instance.get_important_locations_async()
#         return json.dumps(result, ensure_ascii=False)

#     @tool
#     async def background_knowledge_tool() -> str:
#         """使用 GraphRAG 的全局查询功能获取故事的背景知识。"""
#         result = await graphrag_agent_instance.background_knowledge_async()
#         return json.dumps(result, ensure_ascii=False)
    
#     @tool
#     async def get_worldview_tool() -> str:
#         """使用 GraphRAG 的全局查询功能获取故事的世界观和基本设定。"""
#         result = await graphrag_agent_instance.get_worldview_async()
#         return json.dumps(result, ensure_ascii=False)

#     @tool
#     async def local_search_tool(query: str) -> str:
#         """使用 GraphRAG 的局部查询功能进行自定义搜索。输入是一个字符串形式的查询。"""
#         result = await graphrag_agent_instance.local_search_async(query)
#         return json.dumps(result, ensure_ascii=False)

#     @tool
#     async def global_search_tool(query: str) -> str:
#         """使用 GraphRAG 的全局查询功能进行自定义搜索。输入是一个字符串形式的查询。"""
#         result = await graphrag_agent_instance.global_search_async(query)
#         return json.dumps(result, ensure_ascii=False)
#     @tool 
#     async def get_character_profile_tool(character_name: str) -> str:
#         """获取特定人物的详细信息。输入参数character_name是人物名称。"""
#         result = await graphrag_agent_instance.get_character_profile_async(character_name)
#         return json.dumps(result, ensure_ascii=False)
#     @tool
#     async def get_significant_event_tool(event_name: str) -> str:
#         """获取特定事件的详细信息。输入参数event_name是事件名称。"""
#         result = await graphrag_agent_instance.get_significant_event_async(event_name)
#         return json.dumps(result, ensure_ascii=False)

#     @tool
#     async def get_main_theme_tool() -> str:
#         """获取故事的主题。"""
#         result = await graphrag_agent_instance.get_main_theme_async()
#         return json.dumps(result, ensure_ascii=False)
#     @tool 
#     async def get_open_questions_tool() -> str:
#         """获取本书的悬念或者未解决的伏笔。"""
#         result = await graphrag_agent_instance.get_open_questions_async()
#         return json.dumps(result, ensure_ascii=False)
#     @tool
#     async def get_causal_chains_tool(event: str) -> str:
#         """获取给定事件的因果链。可以知道是什么导致的该事件，然后该事件导致了什么样的结果，最后结果又导致了什么样的后果"""
#         result = await graphrag_agent_instance.get_causal_chains_async(event)
#         return json.dumps(result, ensure_ascii=False)
#     @tool
#     async def style_guardrails_tool(persona: str) -> str:
#         """产出风格护栏：允许/禁止的句式、词汇、视角、节奏等（供续写遵守）"""
#         q = f"总结{persona}的叙事风格：允许和禁止的句式、词汇、常见修辞、视角限制、节奏建议，列表输出。"
#         res = await graphrag_agent_instance.global_search_async(q)
#         return json.dumps(res, ensure_ascii=False)

#     @tool
#     async def canon_alignment_tool(text: str) -> str:
#         """评估文本与正史/世界规则一致性（角色OOC/设定违背/历史违背），给要点与依据"""
#         q = f"评估以下文本与正史/世界规则的一致性（角色OOC、设定违背、历史违背各给要点评价与依据）：{text[:3000]}"
#         res = await graphrag_agent_instance.local_search_async(q)
#         return json.dumps(res, ensure_ascii=False)

#     @tool
#     async def contradiction_test_tool(text: str) -> str:
#         """检测文本与原著叙述的冲突点，给出原文证据片段定位"""
#         q = f"找出以下文本与原著叙述的冲突点（逐条列出冲突、对应原著证据ID/短摘）：{text[:3000]}"
#         res = await graphrag_agent_instance.local_search_async(q)
#         return json.dumps(res, ensure_ascii=False)
#     @tool
#     async def get_conflict_tool() -> str:
#         """获取本书最大的冲突。"""
#         result = await graphrag_agent_instance.get_conflict_async()
#         return json.dumps(result, ensure_ascii=False)
#     @tool
#     async def get_related_characters_tool(event: str) -> str:
#         """获取给定事件的关联人物。"""
#         result = await graphrag_agent_instance.get_related_characters_async(event)
#         return json.dumps(result, ensure_ascii=False)
#     @tool
#     async def imagine_conversation_tool(character1_name: str, character2_name: str) -> str:
#         """想象两个角色之间的对话。"""
#         result = await graphrag_agent_instance.imagine_conversation_async(character1_name, character2_name)
#         return json.dumps(result, ensure_ascii=False)
#     @tool
#     async def extract_quotes_tool(name:str, n:int=8) -> str:
#         """获取特定人物的台词。"""
#         result = await graphrag_agent_instance.extract_quotes_async(name, n)
#         return json.dumps(result, ensure_ascii=False)
#     @tool
#     async def narrative_pov_tool() -> str:
#         """获取本书的叙事视角。"""
#         result = await graphrag_agent_instance.narrative_pov_async()
#         return json.dumps(result, ensure_ascii=False)
#     @tool
#     async def get_motifs_symbols_tool(max_items:int=20) -> str:
#         """获取本书的意象/母题/象征。"""
#         result = await graphrag_agent_instance.get_motifs_symbols_async(max_items)
#         return json.dumps(result, ensure_ascii=False)
#     @tool
#     async def build_story_outline_tool(brief:str, target_style:str="紧凑具象") -> str:
#         """基于原著约束，为“{brief}”生成三幕式续写大纲（每幕3-5要点），标注涉及人物/地点/冲突/目标。条目式输出。风格：{target_style}。严禁违反既有设定。"""
#         result = await graphrag_agent_instance.build_story_outline_async(brief, target_style)
#         return json.dumps(result, ensure_ascii=False)
#     @tool
#     async def emotion_curve_tool(scope:str="全书") -> str:
#         """获取本书的情感曲线。"""
#         result = await graphrag_agent_instance.emotion_curve_async(scope)
#         return json.dumps(result, ensure_ascii=False)
#     @tool
#     async def compare_characters_tool(a:str, b:str) -> str:
#         """比较两个角色。"""
#         result = await graphrag_agent_instance.compare_characters_async(a, b)
#         return json.dumps(result, ensure_ascii=False)
    
#     # @tool
#     # async def continue_story_tool(
#     #     brief: str,
#     #     persona: str = "保持与原著一致的叙述者口吻与角色对白风格",
#     #     target_style: str = "紧凑、具象细节、对白推动剧情",
#     #     words_per_scene: int = 600,
#     #     max_iters: int = 2
#     # ) -> str:
#     #     """
#     #     一键续写：大纲->节拍->写作->一致性与冲突检查->必要时修订。返回最终场景文本和校验信息。
#     #     - brief: 用户的续写意图说明
#     #     - persona: 人设与口吻约束
#     #     - target_style: 文风目标
#     #     """
#     #     # 1) 取风格护栏与世界规则
#     #     guard = await graphrag_agent_instance.global_search_async(
#     #         f"总结{persona}的叙事风格：允许/禁止的句式、常见修辞、视角限制、节奏建议，列表输出。"
#     #     )
#     #     world = await graphrag_agent_instance.global_search_async(
#     #         "总结世界观硬性规则（政治/法律/科技/宗教/魔法/经济），违反的后果，列表输出。"
#     #     )

#     #     # 2) 基于原著生成续写大纲与节拍（用 GraphRAG 保守抽纲）
#     #     outline = await graphrag_agent_instance.global_search_async(
#     #         f"基于原著信息，按照三幕式生成续写大纲（每幕3-5要点，标注涉及人物/地点/冲突/目标）；风格：{target_style}；用户意图：{brief}"
#     #     )
#     #     beats = await graphrag_agent_instance.global_search_async(
#     #         f"把以下大纲拆为节拍表（每节拍含：目的、冲突、转折、关键信息、涉及角色、证据需求），用紧凑清单：\n{outline.get('result','')[:2800]}"
#     #     )
#     #     # 选第一条节拍写一个场景（需要更多可拆循环）
#     #     beat_first = "\n".join(beats.get("result","").split("\n")[:10])
#     #     # 2) 基于原著生成续写大纲与节拍（用 GraphRAG 保守抽纲）
#     #     outline = await graphrag_agent_instance.global_search_async(
#     #         f"基于原著信息，按照三幕式生成续写大纲（每幕3-5要点，标注涉及人物/地点/冲突/目标）；风格：{target_style}；用户意图：{brief}"
#     #     )
#     #     beats = await graphrag_agent_instance.global_search_async(
#     #         f"把以下大纲拆为节拍表（每节拍含：目的、冲突、转折、关键信息、涉及角色、证据需求），用紧凑清单：\n{outline.get('result','')[:2800]}"
#     #     )
#     #     # 选第一条节拍写一个场景（需要更多可拆循环）
#     #     beat_first = "\n".join(beats.get("result","").split("\n")[:10])

#     #     # 3) 写场景（用生成型 LLM）
#     #     sys = SystemMessage(content=(
#     #         "你是一名严谨的续写作者，必须遵守原著世界规则与角色性格。"
#     #         "生成文本要可直接发布，避免方向性描述。"
#     #         f"【风格护栏】{guard.get('result','')}\n【世界规则】{world.get('result','')}"
#     #     ))
#     #     user = HumanMessage(content=(
#     #         f"请写一个完整场景（不超过{words_per_scene}词）。"
#     #         f"要求：遵守人物口吻与设定、用对白推动剧情、细节具象、避免与原著冲突。\n"
#     #         f"【节拍】\n{beat_first}\n\n【用户意图】\n{brief}"
#     #     ))
#     #     gen = await llm_gen.ainvoke([sys, user])
#     #     scene = gen.content if hasattr(gen, "content") else str(gen)
#     #     # 3) 写场景（用生成型 LLM）
#     #     sys = SystemMessage(content=(
#     #         "你是一名严谨的续写作者，必须遵守原著世界规则与角色性格。"
#     #         "生成文本要可直接发布，避免方向性描述。"
#     #         f"【风格护栏】{guard.get('result','')}\n【世界规则】{world.get('result','')}"
#     #     ))
#     #     user = HumanMessage(content=(
#     #         f"请写一个完整场景（不超过{words_per_scene}词）。"
#     #         f"要求：遵守人物口吻与设定、用对白推动剧情、细节具象、避免与原著冲突。\n"
#     #         f"【节拍】\n{beat_first}\n\n【用户意图】\n{brief}"
#     #     ))
#     #     gen = await llm_gen.ainvoke([sys, user])
#     #     scene = gen.content if hasattr(gen, "content") else str(gen)

#     #     # 4) 校验 & 可能修订（最多 max_iters 轮）
#     #     issues = []
#     #     for _ in range(max_iters+1):
#     #         # 一致性与冲突检查（用 GraphRAG 做证据对齐）
#     #         canon = await graphrag_agent_instance.local_search_async(
#     #             f"评估文本与正史/世界规则一致性（角色OOC/设定违背/历史违背各给要点与依据）：{scene[:3000]}"
#     #         )
#     #         contra = await graphrag_agent_instance.local_search_async(
#     #             f"找出文本与原著叙述的冲突点（逐条列出冲突、对应原著证据ID/短摘）：{scene[:3000]}"
#     #         )
#     #         hard_fail = ("违背" in canon.get("result","")) or ("冲突" in contra.get("result",""))
#     #     # 4) 校验 & 可能修订（最多 max_iters 轮）
#     #     issues = []
#     #     for _ in range(max_iters+1):
#     #         # 一致性与冲突检查（用 GraphRAG 做证据对齐）
#     #         canon = await graphrag_agent_instance.local_search_async(
#     #             f"评估文本与正史/世界规则一致性（角色OOC/设定违背/历史违背各给要点与依据）：{scene[:3000]}"
#     #         )
#     #         contra = await graphrag_agent_instance.local_search_async(
#     #             f"找出文本与原著叙述的冲突点（逐条列出冲突、对应原著证据ID/短摘）：{scene[:3000]}"
#     #         )
#     #         hard_fail = ("违背" in canon.get("result","")) or ("冲突" in contra.get("result",""))

#     #         if not hard_fail:
#     #             # 收集关键断言证据（可选）
#     #             ev = await graphrag_agent_instance.local_search_async(
#     #                 "为上述续写中关键设定与角色动机找出最有力的证据片段（列章节/段落ID+短摘），最多5条。"
#     #             )
#     #             return json.dumps({
#     #                 "status": "DONE",
#     #                 "outline": outline,
#     #                 "beats": beats,
#     #                 "final_text": scene,
#     #                 "evidence": ev,
#     #                 "issues": issues
#     #             }, ensure_ascii=False)
#     #         if not hard_fail:
#     #             # 收集关键断言证据（可选）
#     #             ev = await graphrag_agent_instance.local_search_async(
#     #                 "为上述续写中关键设定与角色动机找出最有力的证据片段（列章节/段落ID+短摘），最多5条。"
#     #             )
#     #             return json.dumps({
#     #                 "status": "DONE",
#     #                 "outline": outline,
#     #                 "beats": beats,
#     #                 "final_text": scene,
#     #                 "evidence": ev,
#     #                 "issues": issues
#     #             }, ensure_ascii=False)

#     #         issues.append({"canon": canon.get("result",""), "conflict": contra.get("result","")})
#     #         issues.append({"canon": canon.get("result",""), "conflict": contra.get("result","")})

#     #         # 5) 修订指令（再喂回生成 LLM）
#     #         sys2 = SystemMessage(content=(
#     #             "根据评审意见修订文本，务必消除OOC与设定/历史冲突，保留节拍目标与风格护栏。"
#     #             f"【风格护栏】{guard.get('result','')}\n【评审】{json.dumps(issues[-1], ensure_ascii=False)[:1500]}"
#     #         ))
#     #         user2 = HumanMessage(content=(
#     #             f"请在不超过{words_per_scene}词内重写该场景：\n{scene[:2000]}"
#     #         ))
#     #         rev = await llm_gen.ainvoke([sys2, user2])
#     #         scene = rev.content if hasattr(rev, "content") else str(rev)
#     #         # 5) 修订指令（再喂回生成 LLM）
#     #         sys2 = SystemMessage(content=(
#     #             "根据评审意见修订文本，务必消除OOC与设定/历史冲突，保留节拍目标与风格护栏。"
#     #             f"【风格护栏】{guard.get('result','')}\n【评审】{json.dumps(issues[-1], ensure_ascii=False)[:1500]}"
#     #         ))
#     #         user2 = HumanMessage(content=(
#     #             f"请在不超过{words_per_scene}词内重写该场景：\n{scene[:2000]}"
#     #         ))
#     #         rev = await llm_gen.ainvoke([sys2, user2])
#     #         scene = rev.content if hasattr(rev, "content") else str(rev)

#     #     # 达到迭代上限仍有问题
#     #     return json.dumps({
#     #         "status": "BUDGET_EXCEEDED",
#     #         "outline": outline,
#     #         "beats": beats,
#     #         "final_text": scene,
#     #         "issues": issues
#     #     }, ensure_ascii=False)
#     #     # 达到迭代上限仍有问题
#     #     return json.dumps({
#     #         "status": "BUDGET_EXCEEDED",
#     #         "outline": outline,
#     #         "beats": beats,
#     #         "final_text": scene,
#     #         "issues": issues
#     #     }, ensure_ascii=False)
#     tools = [
#         get_characters_tool,
#         get_relationships_tool,
#         get_important_locations_tool,
#         get_significant_event_tool,
#         background_knowledge_tool,
#         get_worldview_tool,
#         local_search_tool,
#         global_search_tool,
#         get_character_profile_tool,
#         get_main_theme_tool,
#         get_open_questions_tool,
#         get_causal_chains_tool,
#         style_guardrails_tool,
#         canon_alignment_tool,
#         contradiction_test_tool,
#         get_conflict_tool,
#         get_related_characters_tool,
#         imagine_conversation_tool,
#         extract_quotes_tool,
#         narrative_pov_tool,
#         get_motifs_symbols_tool, 
#         build_story_outline_tool,
#         emotion_curve_tool,
#         compare_characters_tool,
#         # continue_story_tool
#     ]

#     # 初始化 LLM
#     # 确保你已经设置了 OPENAI_API_KEY 环境变量
#     llm = AzureChatOpenAI(
#         openai_api_version="2024-12-01-preview",
#         azure_deployment="gpt-4o",
#         model_name="gpt-4o",
#         azure_endpoint="https://tcamp.openai.azure.com/",
#         openai_api_key=api_key,
#         temperature=0.3,
#         streaming=True,
#         callbacks=[StreamingStdOutCallbackHandler()]
#     )
#     llm_gen = AzureChatOpenAI(
#         openai_api_version="2024-12-01-preview",
#         azure_deployment="gpt-4o",
#         model_name="gpt-4o",
#         azure_endpoint="https://tcamp.openai.azure.com/",
#         openai_api_key=api_key,
#         temperature=0.85,   # 更高创造性
#         max_tokens=1400     # 续写长度预算（按需调）
#     )


#     prompt = f"""
#     You are a helpful assistant that can answer questions about the data in the tables provided. Your tasks mainly consist of two parts: 1. extract and summarize the information about the book; 2. derivative work based on the book.

#     ---Goal---
# 你是一个智能创作助手，可以进行信息分析和探索，通过系统性的调查来完成复杂的创作任务。
# ## 历史对话
# {{history}}
# ## 用户问题
# {{input}}
# ## 调查周期 (Investigation Cycle)
# 你按照一个持续的周期运作：
# 1. 从多个维度理解用户诉求，拆解用户问题，明确用户意图
# 2. 根据历史对话，整合有用信息以理解任务目标
# 3. 根据已掌握的线索和信息缺口，避免和历史对话中完全相同的工具调用（工具参数一致），选择优先级最高的工具，决定接下来要调用哪个工具
# 4. 当你认为没完成任务时或现有信息无法回答用户问题时，"status_update" 为 "IN_PROGRES"，此时你必须选择一个工具。
# 5. 当你认为历史对话的信息足够你回答用户问题时，"status_update" 为 "DONE"
# ## 可用工具 (Available Tools)
# {{functions}}
# ## 工具使用准则 (Tool Usage Guidelines)
# {{guidelines}}
# ## 注意事项
# {{requirements}}
# 响应格式 (Response Format)
# {{response_format}}
#     """

#     prompt = ChatPromptTemplate.from_messages([
#         ("system", prompt),
#         ("user", "{input}\n\n{agent_scratchpad}"),
#     ])

#     # 创建 Agent
#     agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)

#     # 创建 Agent 执行器
#     return AgentExecutor(agent=agent, tools=tools, verbose=True)

# # --- 主程序入口 ---
# async def main() -> None:
#     graph_agent = GraphAnalysisAgent()

#     # 使用这个实例创建 LangChain Agent
#     agent_executor = create_graphrag_agent(graph_agent)

#     print("LangChain Agent with GraphRAG (Python API) tools is ready. Type 'exit' to quit.")

#     history = []

#     while True:
#         user_query = input("\n请输入你的问题：")
#         history.append({"role": "user", "content": user_query})
#         recent_history = history[-4:]  # 只保留最近的4条历史记录
#         history_text = ""
#         for msg in recent_history:
#             prefix = "用户：" if msg["role"] == "user" else "助手："
#             history_text += f"{prefix}{msg['content']}\n"
#         if user_query.lower() == 'exit':
#             break

#         try:
#             # 使用异步调用，匹配异步工具
#             # response = await agent_executor.ainvoke({"input": user_query, "guidelines": prompt_utils.build_guidelines(), "functions": agent_executor.tools, "requirements": prompt_utils.build_requirements(), "response_format": prompt_utils.build_response_format()})
#             response = await agent_executor.ainvoke({"input": user_query, "guidelines": prompt.build_guidelines(), "functions": agent_executor.tools, "requirements": prompt.build_requirements(), "response_format": prompt.build_response_format(), "history": history_text})
#             # print("\n--- Agent 回答 ---")
#             # print(response.get("output"))
#             # print("--------------------\n")
#             # history.append({"role": "assistant", "content": response.get("output")})
#         except Exception as e:
#             print(f"发生错误：{e}")
#             break


# if __name__ == "__main__":
#     asyncio.run(main())


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


from langchain.agents import tool
from langchain.agents import create_react_agent, AgentExecutor, create_tool_calling_agent
from langchain import hub
from langchain_openai import ChatOpenAI,AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from search.rag_engine import rag_engine
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import prompt_utils
import prompt

class GraphAnalysisAgent:
    def __init__(self):
        self.rag_engine = rag_engine
        
    async def global_search_retrieve_async(self, query: str) -> Dict[str, Any]:
        """全局搜索 - 仅检索阶段，展示RAG召回内容"""
        return await self.rag_engine.global_search_retrieve(query)
    
    async def global_search_generate_async(self, query: str, retrieved_context: Any) -> Dict[str, Any]:
        """全局搜索 - 仅生成阶段，使用预检索的上下文"""
        return await self.rag_engine.global_search_generate(query, retrieved_context)
    
    async def global_search_full_async(self, query: str) -> Dict[str, Any]:
        """全局搜索 - 完整流程（检索+生成）"""
        return await self.rag_engine.global_search_full(query)
    
    async def local_search_retrieve_async(self, query: str) -> Dict[str, Any]:
        """局部搜索 - 仅检索阶段，展示RAG召回内容"""
        return await self.rag_engine.local_search_retrieve(query)
    
    async def local_search_generate_async(self, query: str, retrieved_context: Any) -> Dict[str, Any]:
        """局部搜索 - 仅生成阶段，使用预检索的上下文"""
        return await self.rag_engine.local_search_generate(query, retrieved_context)
    
    async def local_search_full_async(self, query: str) -> Dict[str, Any]:
        """局部搜索 - 完整流程（检索+生成）"""
        return await self.rag_engine.local_search_full(query)

    async def get_characters_async(self) -> Dict[str, Any]:
        return await self.global_search_full_async("列出故事中的所有人物角色")

    async def get_relationships_async(self, p1: str, p2: str) -> Dict[str, Any]:
        return await self.global_search_full_async(f"分析{p1}和{p2}之间的关系")

    async def get_important_locations_async(self) -> Dict[str, Any]:
        return await self.global_search_full_async("分析故事中的重要地点和场景")

    async def background_knowledge_async(self) -> Dict[str, Any]:
        return await self.global_search_full_async("分析故事的背景知识")
    
    async def get_worldview_async(self) -> Dict[str, Any]:
        return await self.global_search_full_async("获取故事的世界观和基本设定")

    async def get_character_profile_async(self, character_name: str) -> Dict[str, Any]:
        return await self.global_search_full_async(f"获取{character_name}的详细信息")
    
    async def get_significant_event_async(self, event_name:str) -> Dict[str, Any]:
        return await self.global_search_full_async(f"获取事件{event_name}的详细信息")
    
    async def get_main_theme_async(self) -> Dict[str, Any]:
        return await self.global_search_full_async("分析故事的主题")
    async def mock_coversation_async(self, character1_name: str, character2_name: str) -> Dict[str, Any]:
        return await self.local_search_full_async(f"模拟{character1_name}和{character2_name}的对话")
    async def get_open_questions_async(self) -> Dict[str, Any]:
        return await self.global_search_full_async("本书有什么悬念或者没有解决的伏笔？")
    async def get_conflict_async(self) -> Dict[str, Any]:
        return await self.global_search_full_async("罗列出本书最大的冲突是什么")
    async def get_related_characters_async(self, event: str) -> Dict[str, Any]:
        return await self.global_search_full_async(f"获取{event}事件的关联人物")
    async def get_causal_chains_async(self, event: str) -> Dict[str, Any]:
        return await self.local_search_full_async(f"获取{event}事件的因果链：前置条件→触发→结果→后果")
    async def style_guardrails_async(self, persona: str) -> Dict[str, Any]:
        return await self.global_search_full_async(f"总结{persona}的叙事风格：允许和禁止的句式、词汇、常见修辞、视角限制、节奏建议，列表输出。")
    async def canon_alignment_async(self, text: str) -> Dict[str, Any]:
        return await self.local_search_full_async(f"评估以下文本与正史/世界规则的一致性（角色OOC、设定违背、历史违背各给要点评价与依据）：{text[:3000]}")
    async def contradiction_test_async(self, text: str) -> Dict[str, Any]:
        return await self.local_search_full_async(f"找出以下文本与原著叙述的冲突点（逐条列出冲突、对应原著证据ID/短摘）：{text[:3000]}")
    async def continue_story_async(self, brief: str, persona: str = "保持与原著一致的叙述者口吻与角色对白风格", target_style: str = "紧凑、具象细节、对白推动剧情", words_per_scene: int = 600, max_iters: int = 2) -> Dict[str, Any]:
        return await self.local_search_full_async(f"为以下大纲续写一个场景（不超过{words_per_scene}词）：{brief[:3000]}")
    async def imagine_conversation_async(self, character1_name: str, character2_name: str) -> Dict[str, Any]:
        return await self.local_search_full_async(f"想象{character1_name}和{character2_name}的对话")
    async def extract_quotes_async(self, name:str, n:int=8) -> Dict[str, Any]:
        q = f"列出{name}最具代表性的台词{n}条（每条<=40字，附章节/段落编号），严格JSON数组："
        return await self.local_search_full_async(q)
    async def narrative_pov_async(self) -> Dict[str, Any]:
        q = """
    分析叙事视角与可靠性：POV类型、切换点、可能偏见/误导的证据。用分点列出，每点附<=40字短摘+章节。
    """
        return await self.global_search_full_async(q)
    async def get_motifs_symbols_async(self, max_items:int=20) -> Dict[str, Any]:
        q = f"""
    抽取意象/母题/象征（最多{max_items}条），严格JSON：
    [{{"motif":"…","meaning":"…","linked_themes":["…"],"chapters":["…"],"evidence":[{{"chapter":"…","quote":"<=40字"}}]}}]
    """
        return await self.local_search_full_async(q)
    async def build_story_outline_async(self, brief:str, target_style:str="紧凑具象") -> Dict[str, Any]:
        q = f"""
    基于原著约束，为"{brief}"生成三幕式续写大纲（每幕3-5要点），标注涉及人物/地点/冲突/目标。条目式输出。
    风格：{target_style}。严禁违反既有设定。
    """
        return await self.global_search_full_async(q)
    async def emotion_curve_async(self, scope:str="全书") -> Dict[str, Any]:
        q = f"提取{scope}的情感曲线关键转折（喜/怒/哀/惧/惊/厌/信），列出转折点章节与触发事件，各给<=40字短摘。"
        return await self.global_search_full_async(q)
    async def compare_characters_async(self, a:str, b:str) -> Dict[str, Any]:
        q = f"""
    比较{a}与{b}，严格JSON：
    {{"values":["…"],"goals":["…"],"methods":["…"],"red_lines":["…"],"decision_style":"冲动|谨慎|算计","evidence":[{{"chapter":"…","quote":"<=40字"}}]}}
    """
        return await self.global_search_full_async(q)
    async def get_people_location_relation_async(self, people:str, location:str, relation:str) -> Dict[str, Any]:
        q = f"""
    分析{people}和{location}之间的关系，严格JSON：
    {{"values":["…"],"goals":["…"],"methods":["…"],"red_lines":["…"],"decision_style":"冲动|谨慎|算计","evidence":[{{"chapter":"…","quote":"<=40字"}}]}}
    """
        return await self.global_search_full_async(q)

# --- 第二步：创建 LangChain Agent ---
def create_graphrag_agent(graphrag_agent_instance: GraphAnalysisAgent) -> AgentExecutor:
    """
    创建并返回一个可以调用 GraphRAG 命令行功能的 LangChain Agent。
    """
    # 使用 @tool 装饰器，将 GraphAnalysisAgent 的方法包装成 LangChain 工具
    # 注意：这里的工具函数需要能够被 Agent 直接调用，所以我们使用闭包来传递实例
    
    # === 新增：RAG检索分离工具 ===
    @tool
    async def global_search_retrieve_tool(query: str) -> str:
        """全局搜索 - 仅检索阶段，展示RAG召回的内容。用户可以看到GraphRAG检索到了哪些相关文档和上下文，但不进行LLM生成。"""
        result = await graphrag_agent_instance.global_search_retrieve_async(query)
        return json.dumps(result, ensure_ascii=False, default=str)
    
    @tool
    async def global_search_generate_tool(query: str, retrieved_context: str) -> str:
        """全局搜索 - 仅生成阶段，使用预检索的上下文进行LLM生成。需要先调用global_search_retrieve_tool获取上下文。"""
        try:
            print(f"🤖 [Agent LLM] 正在使用agent的LLM工具生成全局搜索回答: {query}")
            
            # 解析检索到的上下文 - 增加更健壮的错误处理
            import json
            try:
                if isinstance(retrieved_context, str):
                    # 尝试解析JSON字符串
                    context_data = json.loads(retrieved_context)
                else:
                    # 如果已经是字典，直接使用
                    context_data = retrieved_context
            except json.JSONDecodeError as e:
                print(f"ℹ️ [Agent LLM] 检测到非JSON格式数据，正在转换为字符串格式...")
                # 如果JSON解析失败，尝试直接使用字符串
                context_text = str(retrieved_context)
            else:
                # JSON解析成功，提取上下文文本
                context_text = context_data.get('retrieved_context', {}).get('context_text', '')
                if not context_text:
                    # 如果嵌套结构不存在，尝试其他可能的键
                    context_text = context_data.get('context_text', str(context_data))
            
            # 构建提示
            prompt = f"""基于以下检索到的上下文信息，回答用户的问题：

用户问题：{query}

检索到的上下文：
{context_text}

请基于上述上下文信息，提供详细、准确的回答。要求：
1. 回答要具体详细，包含充分的解释和证据
2. 引用上下文中的具体信息来支持你的回答
3. 如果涉及人物，要说明他们的角色、特点和重要性
4. 如果涉及事件，要描述其背景、过程和影响
5. 回答长度应该在200-500字之间，确保信息充分但不过于冗长"""
            
            # 使用agent的LLM工具进行生成
            from langchain_core.messages import SystemMessage, HumanMessage
            
            messages = [
                SystemMessage(content="你是一个专业的文本分析助手，基于检索到的上下文信息回答问题。请提供详细、具体的回答，包含充分的解释和证据。"),
                HumanMessage(content=prompt)
            ]
            
            response = await llm_gen.ainvoke(messages)
            result_text = response.content if hasattr(response, 'content') else str(response)
            
            print(f"✅ [Agent LLM] 全局搜索生成完成，回答长度: {len(result_text)} 字符")
            
            # 直接返回生成的文本内容，而不是JSON格式
            return result_text
            
        except Exception as e:
            print(f"❌ [Agent LLM] 全局搜索生成失败: {e}")
            return json.dumps({
                "method": "agent_global_generate",
                "query": query,
                "error": str(e),
                "success": False
            }, ensure_ascii=False, default=str)
    
    @tool
    async def local_search_retrieve_tool(query: str) -> str:
        """局部搜索 - 仅检索阶段，展示RAG召回的内容。用户可以看到GraphRAG检索到了哪些相关文档和上下文，但不进行LLM生成。"""
        result = await graphrag_agent_instance.local_search_retrieve_async(query)
        return json.dumps(result, ensure_ascii=False, default=str)
    
    @tool
    async def local_search_generate_tool(query: str, retrieved_context: str) -> str:
        """局部搜索 - 仅生成阶段，使用预检索的上下文进行LLM生成。需要先调用local_search_retrieve_tool获取上下文。"""
        try:
            print(f"🤖 [Agent LLM] 正在使用agent的LLM工具生成局部搜索回答: {query}")
            
            # 解析检索到的上下文 - 增加更健壮的错误处理
            import json
            try:
                if isinstance(retrieved_context, str):
                    # 尝试解析JSON字符串
                    context_data = json.loads(retrieved_context)
                else:
                    # 如果已经是字典，直接使用
                    context_data = retrieved_context
            except json.JSONDecodeError as e:
                print(f"ℹ️ [Agent LLM] 检测到非JSON格式数据，正在转换为字符串格式...")
                # 如果JSON解析失败，尝试直接使用字符串
                context_text = str(retrieved_context)
            else:
                # JSON解析成功，提取上下文文本
                context_text = context_data.get('retrieved_context', {}).get('context_text', '')
                if not context_text:
                    # 如果嵌套结构不存在，尝试其他可能的键
                    context_text = context_data.get('context_text', str(context_data))
            
            # 构建提示
            prompt = f"""基于以下检索到的上下文信息，回答用户的问题：

用户问题：{query}

检索到的上下文：
{context_text}

请基于上述上下文信息，提供详细、准确的回答。要求：
1. 回答要具体详细，包含充分的解释和证据
2. 引用上下文中的具体信息来支持你的回答
3. 如果涉及人物，要说明他们的角色、特点和重要性
4. 如果涉及事件，要描述其背景、过程和影响
5. 回答长度应该在200-500字之间，确保信息充分但不过于冗长"""
            
            # 使用agent的LLM工具进行生成
            from langchain_core.messages import SystemMessage, HumanMessage
            
            messages = [
                SystemMessage(content="你是一个专业的文本分析助手，基于检索到的上下文信息回答问题。请提供详细、具体的回答，包含充分的解释和证据。"),
                HumanMessage(content=prompt)
            ]
            
            response = await llm_gen.ainvoke(messages)
            result_text = response.content if hasattr(response, 'content') else str(response)
            
            print(f"✅ [Agent LLM] 局部搜索生成完成，回答长度: {len(result_text)} 字符")
            
            # 直接返回生成的文本内容，而不是JSON格式
            return result_text
            
        except Exception as e:
            print(f"❌ [Agent LLM] 局部搜索生成失败: {e}")
            return json.dumps({
                "method": "agent_local_generate",
                "query": query,
                "error": str(e),
                "success": False
            }, ensure_ascii=False, default=str)
    
    # === 新增：独立LLM调用工具 ===
    @tool
    async def llm_generate_tool(prompt: str, context: str = "") -> str:
        """独立调用大模型生成回答。输入prompt是生成提示，context是上下文信息（可选）。用户可以看到LLM正在生成内容。"""
        try:
            print(f"🤖 [独立LLM] 正在调用大模型生成回答...")
            print(f"提示: {prompt[:100]}...")
            if context:
                print(f"上下文长度: {len(context)} 字符")
            
            # 使用llm_gen进行生成
            from langchain_core.messages import SystemMessage, HumanMessage
            
            messages = []
            if context:
                messages.append(SystemMessage(content=f"基于以下上下文信息回答问题。请提供详细、具体的回答，包含充分的解释和证据：\n\n{context}"))
            messages.append(HumanMessage(content=prompt))
            
            response = await llm_gen.ainvoke(messages)
            result_text = response.content if hasattr(response, 'content') else str(response)
            
            print(f"✅ [独立LLM] 生成完成，回答长度: {len(result_text)} 字符")
            
            return json.dumps({
                "method": "llm_generate",
                "prompt": prompt,
                "context_length": len(context) if context else 0,
                "response": result_text,
                "success": True
            }, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"❌ [独立LLM] 生成失败: {e}")
            return json.dumps({
                "method": "llm_generate",
                "prompt": prompt,
                "error": str(e),
                "success": False
            }, ensure_ascii=False, default=str)
    
    @tool
    async def llm_analyze_tool(text: str, analysis_type: str = "general") -> str:
        """使用大模型分析文本。输入text是要分析的文本，analysis_type是分析类型（如'character', 'theme', 'plot'等）。"""
        try:
            print(f"🤖 [LLM分析] 正在使用大模型分析文本...")
            print(f"分析类型: {analysis_type}")
            print(f"文本长度: {len(text)} 字符")
            
            # 根据分析类型构建提示
            if analysis_type == "character":
                prompt = f"请分析以下文本中的人物特征、性格、动机等：\n\n{text}"
            elif analysis_type == "theme":
                prompt = f"请分析以下文本的主题、象征意义、深层含义：\n\n{text}"
            elif analysis_type == "plot":
                prompt = f"请分析以下文本的情节发展、冲突、转折点：\n\n{text}"
            else:
                prompt = f"请对以下文本进行{analysis_type}分析：\n\n{text}"
            
            from langchain_core.messages import HumanMessage
            response = await llm_gen.ainvoke([HumanMessage(content=prompt)])
            result_text = response.content if hasattr(response, 'content') else str(response)
            
            print(f"✅ [LLM分析] 分析完成，结果长度: {len(result_text)} 字符")
            
            return json.dumps({
                "method": "llm_analyze",
                "analysis_type": analysis_type,
                "text_length": len(text),
                "analysis_result": result_text,
                "success": True
            }, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"❌ [LLM分析] 分析失败: {e}")
            return json.dumps({
                "method": "llm_analyze",
                "analysis_type": analysis_type,
                "error": str(e),
                "success": False
            }, ensure_ascii=False, default=str)
    
    # === 原有工具 ===
    @tool
    async def get_characters_tool() -> str:
        """使用 GraphRAG 的全局查询功能获取故事中的所有人物角色。"""
        result = await graphrag_agent_instance.get_characters_async()
        return json.dumps(result, ensure_ascii=False, default=str)

    @tool
    async def get_relationships_tool(p1: str, p2: str) -> str:
        """获取两个特定人物之间的关系。输入参数p1和p2是人物名称。如果没有找到两个人物的关系，可以尝试单独查询两个人物的背景信息，并且尝试找到和他们共同相关的人来判断他们之间可能的关系"""
        result = await graphrag_agent_instance.get_relationships_async(p1, p2)
        return json.dumps(result, ensure_ascii=False, default=str)

    @tool
    async def get_important_locations_tool() -> str:
        """使用 GraphRAG 的全局查询功能获取故事中的重要地点。"""
        result = await graphrag_agent_instance.get_important_locations_async()
        return json.dumps(result, ensure_ascii=False, default=str)

    @tool
    async def background_knowledge_tool() -> str:
        """使用 GraphRAG 的全局查询功能获取故事的背景知识。"""
        result = await graphrag_agent_instance.background_knowledge_async()
        return json.dumps(result, ensure_ascii=False, default=str)
    
    @tool
    async def get_worldview_tool() -> str:
        """使用 GraphRAG 的全局查询功能获取故事的世界观和基本设定。"""
        result = await graphrag_agent_instance.get_worldview_async()
        return json.dumps(result, ensure_ascii=False, default=str)
    
    @tool
    async def local_search_tool(query: str) -> str:
        """使用 GraphRAG 的局部查询功能进行自定义搜索。输入是一个字符串形式的查询。"""
        result = await graphrag_agent_instance.local_search_full_async(query)
        return json.dumps(result, ensure_ascii=False, default=str)

    @tool
    async def global_search_tool(query: str) -> str:
        """使用 GraphRAG 的全局查询功能进行自定义搜索。输入是一个字符串形式的查询。"""
        result = await graphrag_agent_instance.global_search_full_async(query)
        return json.dumps(result, ensure_ascii=False, default=str)
    @tool 
    async def get_character_profile_tool(character_name: str) -> str:
        """获取特定人物的详细信息。输入参数character_name是人物名称。"""
        result = await graphrag_agent_instance.get_character_profile_async(character_name)
        return json.dumps(result, ensure_ascii=False, default=str)
    @tool
    async def get_significant_event_tool(event_name: str) -> str:
        """获取特定事件的详细信息。输入参数event_name是事件名称。"""
        result = await graphrag_agent_instance.get_significant_event_async(event_name)
        return json.dumps(result, ensure_ascii=False, default=str)

    @tool
    async def get_main_theme_tool() -> str:
        """获取故事的主题。"""
        result = await graphrag_agent_instance.get_main_theme_async()
        return json.dumps(result, ensure_ascii=False, default=str)
    @tool 
    async def get_open_questions_tool() -> str:
        """获取本书的悬念或者未解决的伏笔。"""
        result = await graphrag_agent_instance.get_open_questions_async()
        return json.dumps(result, ensure_ascii=False, default=str)
    @tool
    async def get_causal_chains_tool(event: str) -> str:
        """获取给定事件的因果链。可以知道是什么导致的该事件，然后该事件导致了什么样的结果，最后结果又导致了什么样的后果"""
        result = await graphrag_agent_instance.get_causal_chains_async(event)
        return json.dumps(result, ensure_ascii=False, default=str)
    @tool
    async def style_guardrails_tool(persona: str) -> str:
        """产出风格护栏：允许/禁止的句式、词汇、视角、节奏等（供续写遵守）"""
        q = f"总结{persona}的叙事风格：允许和禁止的句式、词汇、常见修辞、视角限制、节奏建议，列表输出。"
        res = await graphrag_agent_instance.global_search_full_async(q)
        return json.dumps(res, ensure_ascii=False, default=str)

    @tool
    async def canon_alignment_tool(text: str) -> str:
        """评估文本与正史/世界规则一致性（角色OOC/设定违背/历史违背），给要点与依据"""
        q = f"评估以下文本与正史/世界规则的一致性（角色OOC、设定违背、历史违背各给要点评价与依据）：{text[:3000]}"
        res = await graphrag_agent_instance.local_search_full_async(q)
        return json.dumps(res, ensure_ascii=False, default=str)

    @tool
    async def contradiction_test_tool(text: str) -> str:
        """检测文本与原著叙述的冲突点，给出原文证据片段定位"""
        q = f"找出以下文本与原著叙述的冲突点（逐条列出冲突、对应原著证据ID/短摘）：{text[:3000]}"
        res = await graphrag_agent_instance.local_search_full_async(q)
        return json.dumps(res, ensure_ascii=False, default=str)
    @tool
    async def get_conflict_tool() -> str:
        """获取本书最大的冲突。"""
        result = await graphrag_agent_instance.get_conflict_async()
        return json.dumps(result, ensure_ascii=False, default=str)
    @tool
    async def get_related_characters_tool(event: str) -> str:
        """获取给定事件的关联人物。"""
        result = await graphrag_agent_instance.get_related_characters_async(event)
        return json.dumps(result, ensure_ascii=False, default=str)
    @tool
    async def imagine_conversation_tool(character1_name: str, character2_name: str) -> str:
        """想象两个角色之间的对话。"""
        result = await graphrag_agent_instance.imagine_conversation_async(character1_name, character2_name)
        return json.dumps(result, ensure_ascii=False, default=str)
    @tool
    async def extract_quotes_tool(name:str, n:int=8) -> str:
        """获取特定人物的台词。"""
        result = await graphrag_agent_instance.extract_quotes_async(name, n)
        return json.dumps(result, ensure_ascii=False, default=str)
    @tool
    async def narrative_pov_tool() -> str:
        """获取本书的叙事视角。"""
        result = await graphrag_agent_instance.narrative_pov_async()
        return json.dumps(result, ensure_ascii=False, default=str)
    @tool
    async def get_motifs_symbols_tool(max_items:int=20) -> str:
        """获取本书的意象/母题/象征。"""
        result = await graphrag_agent_instance.get_motifs_symbols_async(max_items)
        return json.dumps(result, ensure_ascii=False, default=str)
    @tool
    async def build_story_outline_tool(brief:str, target_style:str="紧凑具象") -> str:
        """基于原著约束，为"{brief}"生成三幕式续写大纲（每幕3-5要点），标注涉及人物/地点/冲突/目标。条目式输出。风格：{target_style}。严禁违反既有设定。"""
        result = await graphrag_agent_instance.build_story_outline_async(brief, target_style)
        return json.dumps(result, ensure_ascii=False, default=str)
    @tool
    async def emotion_curve_tool(scope:str="全书") -> str:
        """获取本书的情感曲线。"""
        result = await graphrag_agent_instance.emotion_curve_async(scope)
        return json.dumps(result, ensure_ascii=False, default=str)
    @tool
    async def compare_characters_tool(a:str, b:str) -> str:
        """比较两个角色。"""
        result = await graphrag_agent_instance.compare_characters_async(a, b)
        return json.dumps(result, ensure_ascii=False, default=str)
    
    @tool
    async def system_status_tool() -> str:
        """获取系统状态信息，包括可用工具、处理能力等"""
        return json.dumps({
            "system_status": "running",
            "available_tools": [
                "global_search_tool", "local_search_tool", "get_characters_tool",
                "get_relationships_tool", "background_knowledge_tool", "llm_generate_tool",
                "llm_analyze_tool", "get_character_profile_tool", "get_worldview_tool"
            ],
            "capabilities": [
                "人物分析", "关系分析", "背景知识查询", "情节分析", "文本生成", "创意写作"
            ],
            "specialization": "《沙丘》(Dune)系列小说分析",
            "note": "系统已优化，支持详细回答和用户友好的状态提示"
        }, ensure_ascii=False, default=str)
    @tool 
    async def get_people_location_relation_tool(people:str, location:str, relation:str) -> str:
        """获取特定人物和地点之间的关系。"""
        result = await graphrag_agent_instance.get_people_location_relation_async(people, location, relation)
        return json.dumps(result, ensure_ascii=False, default=str)
    tools = [
        # === 新增的RAG检索分离工具 ===
        global_search_retrieve_tool,
        global_search_generate_tool,
        local_search_retrieve_tool,
        local_search_generate_tool,
        
        # === 新增：独立LLM调用工具 ===
        # llm_generate_tool,
        # llm_analyze_tool,
        
        # === 原有工具 ===
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
        system_status_tool,
        get_people_location_relation_tool,
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
        max_tokens=2000,  # 从800增加到2000
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
        max_tokens=2000     # 从1000增加到2000
    )


    prompt = f"""
你是一个智能创作助手，专门分析《沙丘》(Dune)系列小说，可以进行信息分析和探索，通过系统性的调查来完成复杂的创作任务。

## 重要说明：RAG检索分离工具和独立LLM调用
现在你有新的工具可以分离RAG的检索和生成过程，以及独立的LLM调用：

### RAG检索分离工具：
- **global_search_retrieve_tool**: 仅进行全局搜索的检索，展示GraphRAG召回的内容
- **global_search_generate_tool**: 使用预检索的上下文进行LLM生成
- **local_search_retrieve_tool**: 仅进行局部搜索的检索，展示GraphRAG召回的内容  
- **local_search_generate_tool**: 使用预检索的上下文进行LLM生成

### 独立LLM调用工具：
- **llm_generate_tool**: 独立调用大模型生成回答，用户可以清楚看到LLM正在生成内容
- **llm_analyze_tool**: 使用大模型分析文本，支持不同类型的分析（character, theme, plot等）

### 使用建议：
1. **展示RAG过程**：先调用 *_retrieve_tool 展示检索到的内容，再调用 *_generate_tool 进行LLM生成
2. **独立LLM调用**：当需要创造性内容或复杂分析时，使用 llm_generate_tool 或 llm_analyze_tool
3. **完整流程**：或者直接使用原有的完整工具（如 global_search_tool）

### 用户可见性：
- 🔍 [RAG检索] 表示正在检索相关信息
- 🤖 [LLM生成] 表示正在调用大模型生成内容
- ✅ 表示操作完成
- ❌ 表示操作失败

### 智能决策指南：
- **人物相关问题**：优先使用 get_character_profile_tool 或 get_characters_tool
- **关系分析**：使用 get_relationships_tool 分析人物关系
- **背景知识**：使用 background_knowledge_tool 或 get_worldview_tool
- **情节分析**：使用 global_search_tool 进行全局分析
- **具体细节**：使用 local_search_tool 进行精确检索
- **创作任务**：使用 llm_generate_tool 进行创造性生成

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

    print("=" * 60)
    print("🤖 《沙丘》智能分析助手已启动")
    print("=" * 60)
    print("📚 专精：《沙丘》(Dune)系列小说分析")
    print("🔧 功能：人物分析、关系分析、背景知识、情节分析、创意写作")
    print("💡 提示：输入 'help' 查看帮助，输入 'exit' 退出")
    print("=" * 60)
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
        elif user_query.lower() == 'help':
            print("\n" + "=" * 60)
            print("📖 《沙丘》智能分析助手 - 使用帮助")
            print("=" * 60)
            print("🎯 主要功能：")
            print("  • 人物分析：查询角色背景、性格、动机")
            print("  • 关系分析：分析人物之间的关系")
            print("  • 背景知识：了解世界观、设定、历史")
            print("  • 情节分析：分析故事发展、冲突、转折")
            print("  • 创意写作：基于原著进行续写、对话生成")
            print("\n💬 示例问题：")
            print("  • '保罗·阿特雷德斯的性格特点是什么？'")
            print("  • '保罗和杰西卡的关系如何？'")
            print("  • '香料在沙丘世界中的作用是什么？'")
            print("  • 'Bene Gesserit姐妹会的目标是什么？'")
            print("  • '请分析沙丘的主要冲突'")
            print("\n🔧 系统状态：")
            print("  • 输入 'status' 查看系统状态")
            print("  • 输入 'exit' 退出程序")
            print("=" * 60)
            continue
        elif user_query.lower() == 'status':
            print("\n🔧 正在获取系统状态...")
            try:
                status_response = await agent_executor.ainvoke({"input": "请调用system_status_tool获取系统状态信息"})
                if status_response and status_response.get("output"):
                    print(status_response.get("output"))
                else:
                    print("❌ 无法获取系统状态")
            except Exception as e:
                print(f"❌ 获取系统状态失败：{e}")
            continue
        
        try:
            print(f"\n🤖 [Agent处理] 正在处理您的问题...")
            # 使用异步调用，匹配异步工具
            response = await agent_executor.ainvoke({"input": user_query, "guidelines": prompt.build_guidelines(), "functions": agent_executor.tools, "requirements": prompt.build_requirements(), "response_format": prompt.build_response_format(), "history": history_text})
            
            # 显示Agent的回答
            if response and response.get("output"):
                print(f"\n📝 [Agent回答]")
                print("=" * 50)
                print(response.get("output"))
                print("=" * 50)
                history.append({"role": "assistant", "content": response.get("output")})
            else:
                print("❌ [错误] Agent没有返回有效回答")
                
        except Exception as e:
            print(f"❌ [错误] 发生错误：{e}")
            break


if __name__ == "__main__":
    asyncio.run(main())