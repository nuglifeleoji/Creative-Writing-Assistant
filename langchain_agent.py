import os
import json
import asyncio
from typing import Dict, Any

# 确保你已经安装了以下库
# pip install langchain langchain-openai

# 注意配置OPENAI_API_KEY以及graphrag所在路径(代码第172行)

from dotenv import load_dotenv

load_dotenv("./.env")

# 优先读取 OPENAI_API_KEY，其次 AZURE_OPENAI_API_KEY，不要把密钥当作环境变量名
api_key =os.getenv("AZURE_OPENAI_API_KEY") or ""

import tiktoken
from langchain.agents import tool
from langchain.agents import create_react_agent, AgentExecutor, create_tool_calling_agent
from langchain import hub
from langchain_openai import ChatOpenAI,AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from search.rag_engine import rag_engine, multi_book_manager, RAGEngine
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import prompt_utils
import prompt

from langchain.memory import ConversationSummaryBufferMemory
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

# 1. 初始化一个用于总结的LLM
# 可以用一个便宜、快速的模型来做总结，也可以用主模型
llm_hist = AzureChatOpenAI(
        openai_api_version="2024-12-01-preview",
        azure_deployment="gpt-4o",
        model_name="gpt-4o",
        azure_endpoint="https://tcamp.openai.azure.com/",
        openai_api_key=api_key,
        temperature=0.1,   # 更高创造性
        max_tokens=2000     # 从1000增加到2000
)

# 2. 创建带总结功能的Memory
# 当token超过1000时，开始将旧消息总结
memory = ConversationSummaryBufferMemory(
    llm=llm_hist,
    max_token_limit=1500,  # 设置token限制
    memory_key="chat_history", # 与prompt中的key对应
    return_messages=True,
)


class GraphAnalysisAgent:
    def __init__(self, use_multi_book=True):
        self.use_multi_book = use_multi_book
        if use_multi_book:
            self.rag_engine = multi_book_manager
            self.current_engine = None
        else:
            self.rag_engine = rag_engine
            self.current_engine = rag_engine
        
    def add_book(self, book_name: str, book_folder: str):
        """添加新书本"""
        if self.use_multi_book:
            self.rag_engine.add_book(book_name, book_folder)
        else:
            print("当前使用的是单书本引擎，请设置 use_multi_book=True 来启用多书本功能")
    
    def switch_book(self, book_name: str):
        """切换到指定书本"""
        if self.use_multi_book:
            self.rag_engine.switch_book(book_name)
            self.current_engine = self.rag_engine.get_current_engine()
        else:
            print("当前使用的是单书本引擎，请设置 use_multi_book=True 来启用多书本功能")
    
    def list_books(self):
        """列出所有可用的书本"""
        if self.use_multi_book:
            return self.rag_engine.list_books()
        else:
            return ["default_book"]
    
    def get_current_book(self):
        """获取当前书本名称"""
        if self.use_multi_book:
            return self.rag_engine.get_current_book()
        else:
            return "default_book"
    
    def _get_engine(self):
        """获取当前引擎"""
        if self.use_multi_book:
            if self.current_engine is None:
                # 如果还没有选择书本，返回None让agent提示用户选择
                return None
            return self.current_engine
        else:
            return self.rag_engine
        
    async def global_search_retrieve_async(self, query: str) -> Dict[str, Any]:
        """全局搜索 - 仅检索阶段，展示RAG召回内容"""
        engine = self._get_engine()
        if engine is None:
            return {
                "method": "global_retrieve",
                "query": query,
                "error": "请先选择一本书本",
                "success": False,
                "need_book_selection": True
            }
        return await engine.global_search_retrieve(query)
    
    async def global_search_generate_async(self, query: str, retrieved_context: Any) -> Dict[str, Any]:
        """全局搜索 - 仅生成阶段，使用预检索的上下文"""
        engine = self._get_engine()
        if engine is None:
            return {
                "method": "global_generate",
                "query": query,
                "error": "请先选择一本书本",
                "success": False,
                "need_book_selection": True
            }
        return await engine.global_search_generate(query, retrieved_context)
    
    async def global_search_full_async(self, query: str) -> Dict[str, Any]:
        """全局搜索 - 完整流程（检索+生成）"""
        engine = self._get_engine()
        if engine is None:
            return {
                "method": "global_full",
                "query": query,
                "error": "请先选择一本书本",
                "success": False,
                "need_book_selection": True
            }
        return await engine.global_search_full(query)
    
    async def local_search_retrieve_async(self, query: str) -> Dict[str, Any]:
        """局部搜索 - 仅检索阶段，展示RAG召回内容"""
        engine = self._get_engine()
        if engine is None:
            return {
                "method": "local_retrieve",
                "query": query,
                "error": "请先选择一本书本",
                "success": False,
                "need_book_selection": True
            }
        return await engine.local_search_retrieve(query)
    
    async def local_search_generate_async(self, query: str, retrieved_context: Any) -> Dict[str, Any]:
        """局部搜索 - 仅生成阶段，使用预检索的上下文"""
        engine = self._get_engine()
        if engine is None:
            return {
                "method": "local_generate",
                "query": query,
                "error": "请先选择一本书本",
                "success": False,
                "need_book_selection": True
            }
        return await engine.local_search_generate(query, retrieved_context)
    
    async def local_search_full_async(self, query: str) -> Dict[str, Any]:
        """局部搜索 - 完整流程（检索+生成）"""
        engine = self._get_engine()
        if engine is None:
            return {
                "method": "local_full",
                "query": query,
                "error": "请先选择一本书本",
                "success": False,
                "need_book_selection": True
            }
        return await engine.local_search_full(query)

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

# --- 第二步：创建 LangChain Agent ---
def create_graphrag_agent(graphrag_agent_instance: GraphAnalysisAgent) -> AgentExecutor:
    """
    创建并返回一个可以调用 GraphRAG 命令行功能的 LangChain Agent。
    """
    # 使用 @tool 装饰器，将 GraphAnalysisAgent 的方法包装成 LangChain 工具
    # 注意：这里的工具函数需要能够被 Agent 直接调用，所以我们使用闭包来传递实例
    
    @tool
    async def list_available_books_tool() -> str:
        """列出所有可用的书本。如果还没有添加任何书本，会提示用户添加书本。"""
        books = graphrag_agent_instance.list_books()
        if not books:
            return json.dumps({
                "message": "还没有添加任何书本。请使用 add_book_tool 添加书本。",
                "books": [],
                "success": False
            }, ensure_ascii=False)
        
        current_book = graphrag_agent_instance.get_current_book()
        return json.dumps({
            "message": f"可用的书本：{', '.join(books)}。当前选择的书本：{current_book}",
            "books": books,
            "current_book": current_book,
            "success": True
        }, ensure_ascii=False)
    
    @tool
    async def add_book_tool(book_name: str, book_folder: str) -> str:
        """添加新书本到系统中。book_name是书本的显示名称，book_folder是书本数据文件夹的路径。"""
        try:
            graphrag_agent_instance.add_book(book_name, book_folder)
            return json.dumps({
                "message": f"成功添加书本：{book_name} -> {book_folder}",
                "success": True
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "message": f"添加书本失败：{str(e)}",
                "success": False
            }, ensure_ascii=False)
    
    @tool
    async def switch_book_tool(book_name: str) -> str:
        """切换到指定的书本。book_name是要切换到的书本名称。"""
        try:
            graphrag_agent_instance.switch_book(book_name)
            return json.dumps({
                "message": f"成功切换到书本：{book_name}",
                "current_book": book_name,
                "success": True
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "message": f"切换书本失败：{str(e)}",
                "success": False
            }, ensure_ascii=False)
    
    @tool
    async def get_current_book_tool() -> str:
        """获取当前选择的书本名称。"""
        current_book = graphrag_agent_instance.get_current_book()
        return json.dumps({
            "message": f"当前选择的书本：{current_book}",
            "current_book": current_book,
            "success": True
        }, ensure_ascii=False)

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
        # 书本管理工具（优先级最高）
        list_available_books_tool,
        add_book_tool,
        switch_book_tool,
        get_current_book_tool,
        
        # === 新增的RAG检索分离工具 ===
        # global_search_retrieve_tool,
        # # global_search_generate_tool,
        # local_search_retrieve_tool,
        # local_search_generate_tool,
        
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

# ### RAG检索分离工具：
# - **global_search_retrieve_tool**: 仅进行全局搜索的检索，展示GraphRAG召回的内容
# - **global_search_generate_tool**: 使用预检索的上下文进行LLM生成
# - **local_search_retrieve_tool**: 仅进行局部搜索的检索，展示GraphRAG召回的内容  
# - **local_search_generate_tool**: 使用预检索的上下文进行LLM生成

# ### 独立LLM调用工具：
# - **llm_generate_tool**: 独立调用大模型生成回答，用户可以清楚看到LLM正在生成内容
# - **llm_analyze_tool**: 使用大模型分析文本，支持不同类型的分析（character, theme, plot等）


# ## 重要说明：RAG检索分离工具和独立LLM调用
# 现在你有新的工具可以分离RAG的检索和生成过程，以及独立的LLM调用：



# ### 使用建议：
# 1. **展示RAG过程**：先调用 *_retrieve_tool 展示检索到的内容，再调用 *_generate_tool 进行LLM生成
# 2. **独立LLM调用**：当需要创造性内容或复杂分析时，使用 llm_generate_tool 或 llm_analyze_tool
# 3. **完整流程**：或者直接使用原有的完整工具（如 global_search_tool）

# ### 用户可见性：
# - 🔍 [RAG检索] 表示正在检索相关信息
# - 🤖 [LLM生成] 表示正在调用大模型生成内容
# - ✅ 表示操作完成
# - ❌ 表示操作失败

# ### 智能决策指南：
# - **人物相关问题**：优先使用 get_character_profile_tool 或 get_characters_tool
# - **关系分析**：使用 get_relationships_tool 分析人物关系
# - **背景知识**：使用 background_knowledge_tool 或 get_worldview_tool
# - **情节分析**：使用 global_search_tool 进行全局分析
# - **具体细节**：使用 local_search_tool 进行精确检索
# - **创作任务**：使用 llm_generate_tool 进行创造性生成

    # 将 prompt 字符串重命名为 prompt_text，避免与 prompt 模块冲突
    prompt_text = f"""
你是一个智能创作助手，可以进行信息分析和探索，通过系统性的调查来完成复杂的创作任务。

### 书本管理（优先级最高）：
- **list_available_books_tool**: 列出所有可用的书本
- **add_book_tool**: 添加新书本到系统中
- **switch_book_tool**: 切换到指定的书本
- **get_current_book_tool**: 获取当前选择的书本

### 历史记录
{{chat_history}}

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

    prompt_obj = ChatPromptTemplate.from_messages([
        ("system", prompt_text),  # 使用 prompt_text 而不是 prompt
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 使用 partial 来预设变量值
    final_prompt = prompt_obj.partial(
        functions=tools,
        guidelines=prompt.build_guidelines(),  # 现在可以正确调用 prompt 模块
        requirements=prompt.build_requirements(),
        response_format=prompt.build_response_format(),
        history=""  # 添加空的history变量
    )

    # 创建 Agent
    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=final_prompt)

    # 创建 Agent 执行器
    return AgentExecutor(agent=agent, tools=tools, memory=memory, verbose=True)

# --- 主程序入口 ---
async def main() -> None:
    graph_agent = GraphAnalysisAgent(use_multi_book=True)

    # 自动加载所有可用的书本
    print("📚 正在自动加载所有可用的书本...")
    
    # 定义要加载的书本列表
    books_to_load = [
        ("book4", "./book4/output"),
        ("book5", "./book5/output"), 
        ("book6", "./book6/output"),
        ("tencent", "./tencent/output"),
        ("default", "./rag/output")  # 默认的rag/output
    ]
    
    loaded_books = []
    for book_name, book_path in books_to_load:
        try:
            # 检查路径是否存在
            if os.path.exists(book_path):
                # 检查是否包含必要的文件
                required_files = ["communities.parquet", "entities.parquet", "community_reports.parquet", "relationships.parquet", "text_units.parquet"]
                missing_files = [f for f in required_files if not os.path.exists(os.path.join(book_path, f))]
                
                if not missing_files:
                    graph_agent.add_book(book_name, book_path)
                    loaded_books.append(book_name)
                    print(f"✅ 成功加载书本: {book_name} -> {book_path}")
                else:
                    print(f"⚠️ 跳过 {book_name}: 缺少必要文件 {missing_files}")
            else:
                print(f"⚠️ 跳过 {book_name}: 路径不存在 {book_path}")
        except Exception as e:
            print(f"❌ 加载 {book_name} 失败: {e}")
    
    print(f"✅ 总共加载了 {len(loaded_books)} 本书: {', '.join(loaded_books)}")
    
    # 如果有书本加载成功，自动选择第一本
    if loaded_books:
        first_book = loaded_books[0]
        graph_agent.switch_book(first_book)
        print(f"🔄 自动切换到第一本书: {first_book}")
    else:
        print("⚠️ 没有加载到任何书本，请手动添加书本")

    # 使用这个实例创建 LangChain Agent
    agent_executor = create_graphrag_agent(graph_agent)

    print("LangChain Agent with GraphRAG (Python API) tools is ready. Type 'exit' to quit.")
    
    while True:
        user_query = input("\n请输入你的问题：")
        if user_query.lower() == 'exit':
            break

        try:
            # 使用异步调用，匹配异步工具
            response = await agent_executor.ainvoke({
                "input": user_query
            })
            
            # 恢复输出显示
            print("\n--- Agent 回答 ---")
            print(response.get("output"))
            print("--------------------\n")
            
        except Exception as e:
            print(f"发生错误：{e}")
            break


if __name__ == "__main__":
    asyncio.run(main())
