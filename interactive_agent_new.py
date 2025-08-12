import os
import json
import asyncio
import tiktoken
from typing import Dict, Any

# 确保你已经安装了以下库
# pip install langchain langchain-openai

# 注意配置OPENAI_API_KEY以及graphrag所在路径(代码第172行)

from dotenv import load_dotenv

load_dotenv("./.env")

# 优先读取 OPENAI_API_KEY，其次 AZURE_OPENAI_API_KEY，不要把密钥当作环境变量名
api_key =os.getenv("AZURE_OPENAI_API_KEY") or ""

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
        return await self.local_search_full_async(f"获取{character_name}的详细信息")
    
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

    # 初始化 LLM（提前定义，供工具使用）
    # 确保你已经设置了 OPENAI_API_KEY 环境变量
    llm = AzureChatOpenAI(
        openai_api_version="2025-01-01-preview",
        azure_deployment="gpt-4.1",
        model_name="gpt-4.1",
        azure_endpoint="https://tcamp.openai.azure.com/",
        openai_api_key=api_key,
        temperature=0.3,
        max_tokens=2000,  # 从800增加到2000
        streaming=True,
        callbacks=[StreamingStdOutCallbackHandler()]
    )
    llm_gen = AzureChatOpenAI(
        openai_api_version="2025-01-01-preview",
        azure_deployment="gpt-4.1",
        model_name="gpt-4.1",
        azure_endpoint="https://tcamp.openai.azure.com/",
        openai_api_key=api_key,
        temperature=0.85,   # 更高创造性
        max_tokens=2000     # 从1000增加到2000
    )

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
    
    # === 新增：分块处理工具 ===
    @tool
    async def parallel_chunk_analysis_tool(retrieved_context: str, query: str, analysis_type: str = "general") -> str:
        """
        对RAG检索到的内容进行分块并行分析
        
        Args:
            retrieved_context: RAG检索到的完整内容（JSON格式）
            query: 原始查询
            analysis_type: 分析类型 (general, character, theme, plot, relationship等)
        """
        try:
            print(f"🔄 [分块分析] 开始对检索内容进行分块并行分析")
            
            # 解析检索上下文
            if isinstance(retrieved_context, str):
                try:
                    context_data = json.loads(retrieved_context)
                except:
                    context_data = {"full_text": retrieved_context}
            else:
                context_data = retrieved_context
            
            # 获取分块信息
            chunks = context_data.get("chunks", [])
            if not chunks:
                # 如果没有分块，使用完整文本
                full_text = context_data.get("full_text", str(context_data))
                # 手动分块
                token_encoder = tiktoken.get_encoding("cl100k_base")
                tokens = token_encoder.encode(full_text)
                
                chunk_size = 20000
                overlap = 2000
                chunks = []
                
                for i in range(0, len(tokens), chunk_size - overlap):
                    chunk_tokens = tokens[i:i + chunk_size]
                    chunk_text = token_encoder.decode(chunk_tokens)
                    chunks.append({
                        "chunk_id": len(chunks),
                        "text": chunk_text,
                        "chunk_tokens": len(chunk_tokens)
                    })
            
            print(f"📊 [分块分析] 将处理 {len(chunks)} 个分块")
            
            # 根据分析类型选择提示词
            analysis_prompts = {
                "general": f"基于以下内容回答问题：{query}\\n\\n请提供详细、准确的分析。",
                "character": f"从人物角度分析以下内容，重点关注：{query}\\n\\n请识别相关人物、性格特点、行为动机等。",
                "theme": f"从主题角度分析以下内容，重点关注：{query}\\n\\n请识别主要主题、象征意义、深层含义等。",
                "plot": f"从情节角度分析以下内容，重点关注：{query}\\n\\n请识别关键事件、因果关系、情节发展等。",
                "relationship": f"从关系角度分析以下内容，重点关注：{query}\\n\\n请识别人物关系、交互模式、关系发展等。"
            }
            
            base_prompt = analysis_prompts.get(analysis_type, analysis_prompts["general"])
            
            # 并行处理每个分块
            async def analyze_chunk(chunk):
                chunk_id = chunk.get("chunk_id", "unknown")
                chunk_text = chunk.get("text", "")
                
                print(f"  📝 [分块 {chunk_id}] 正在分析 ({chunk.get('chunk_tokens', 0)} tokens)")
                
                prompt = f"{base_prompt}\\n\\n=== 内容分块 {chunk_id} ===\\n{chunk_text}"
                
                try:
                    # 使用 llm_gen 进行分析
                    response = await llm_gen.ainvoke([HumanMessage(content=prompt)])
                    
                    return {
                        "chunk_id": chunk_id,
                        "analysis": response.content,
                        "success": True,
                        "chunk_tokens": chunk.get("chunk_tokens", 0)
                    }
                except Exception as e:
                    print(f"    ❌ [分块 {chunk_id}] 分析失败: {e}")
                    return {
                        "chunk_id": chunk_id,
                        "analysis": f"分析失败: {str(e)}",
                        "success": False,
                        "error": str(e)
                    }
            
            # 并行执行所有分块分析
            import asyncio
            chunk_results = await asyncio.gather(*[analyze_chunk(chunk) for chunk in chunks])
            
            # 统计结果
            successful_chunks = [r for r in chunk_results if r.get("success", False)]
            failed_chunks = [r for r in chunk_results if not r.get("success", False)]
            
            print(f"✅ [分块分析] 完成：{len(successful_chunks)}/{len(chunks)} 个分块成功")
            
            # 为了避免返回的JSON过大，对分析结果进行严格裁剪
            processed_results = []
            for result in chunk_results:
                if result.get("success", False):
                    analysis_content = result.get("analysis", "")
                    # 更严格的裁剪：最多保留2000字符
                    max_analysis_length = 2000
                    if len(analysis_content) > max_analysis_length:
                        truncated_analysis = analysis_content[:max_analysis_length-150] + f"\\n\\n[注：此分析结果已裁剪，原长度 {len(analysis_content)} 字符，已压缩以避免上下文超限]"
                    else:
                        truncated_analysis = analysis_content
                    
                    processed_results.append({
                        "chunk_id": result.get("chunk_id"),
                        "analysis": truncated_analysis,
                        "success": True,
                        "chunk_tokens": result.get("chunk_tokens", 0),
                        "original_length": len(analysis_content),
                        "compressed": len(analysis_content) > max_analysis_length
                    })
                else:
                    processed_results.append(result)
            
            # 统计压缩情况
            compressed_count = sum(1 for r in processed_results if r.get("compressed", False))
            if compressed_count > 0:
                print(f"📉 [结果压缩] {compressed_count}/{len(processed_results)} 个分析结果已压缩")
            
            result = {
                "method": "parallel_chunk_analysis",
                "query": query,
                "analysis_type": analysis_type,
                "total_chunks": len(chunks),
                "successful_chunks": len(successful_chunks),
                "failed_chunks": len(failed_chunks),
                "chunk_analyses": processed_results,
                "ready_for_summary": True,
                # "note": "分块分析完成，结果已严格压缩以避免上下文超限",
                "compression_applied": True,
                "compressed_count": compressed_count
            }
            
            return json.dumps(result, ensure_ascii=False, default=str)
            
        except Exception as e:
            print(f"❌ [分块分析] 整体失败: {e}")
            return json.dumps({
                "method": "parallel_chunk_analysis",
                "error": str(e),
                "success": False
            }, ensure_ascii=False, default=str)
    
    @tool
    async def summary_chunk_results_tool(chunk_analysis_results: str, query: str, summary_focus: str = "comprehensive") -> str:
        """
        对分块分析结果进行总结（支持大量分块，自动处理上下文限制）
        
        Args:
            chunk_analysis_results: 分块分析的结果（JSON格式）
            query: 原始查询
            summary_focus: 总结重点 (comprehensive, key_points, detailed, concise)
        """
        try:
            print(f"📋 [结果总结] 开始总结分块分析结果")
            
            # 解析分块分析结果
            if isinstance(chunk_analysis_results, str):
                try:
                    results_data = json.loads(chunk_analysis_results)
                except:
                    results_data = {"chunk_analyses": [{"analysis": chunk_analysis_results}]}
            else:
                results_data = chunk_analysis_results
            
            chunk_analyses = results_data.get("chunk_analyses", [])
            successful_analyses = [r for r in chunk_analyses if r.get("success", False)]
            
            if not successful_analyses:
                return json.dumps({
                    "method": "summary_chunk_results",
                    "error": "没有成功的分块分析结果可供总结",
                    "success": False
                }, ensure_ascii=False, default=str)
            
            print(f"📊 [结果总结] 总结 {len(successful_analyses)} 个成功的分析结果")
            
            # 使用tiktoken估算token数量，避免上下文超限
            token_encoder = tiktoken.get_encoding("cl100k_base")
            
            # 构建总结提示词模板
            summary_prompts = {
                "comprehensive": f"""请基于以下多个分块的分析结果，对查询"{query}"提供全面、详细的回答。

请：
1. 整合所有分块的关键信息
2. 消除重复内容  
3. 按逻辑顺序组织信息
4. 提供具体的例证和细节
5. 给出完整、连贯的答案

各分块分析结果：""",
                
                "key_points": f"""请基于以下多个分块的分析结果，提取关于"{query}"的关键要点。

请以要点形式总结：
1. 主要发现（3-5个要点）
2. 关键信息
3. 重要细节
4. 结论

各分块分析结果：""",
                
                "detailed": f"""请基于以下多个分块的分析结果，对查询"{query}"提供详细深入的分析。

请包括：
1. 背景信息
2. 详细分析
3. 具体例证
4. 深层含义
5. 相关联系

各分块分析结果：""",
                
                "concise": f"""请基于以下多个分块的分析结果，对查询"{query}"提供简洁精准的回答。

请用简洁语言概括：
1. 核心答案
2. 主要支撑信息
3. 关键结论

各分块分析结果："""
            }
            
            base_prompt = summary_prompts.get(summary_focus, summary_prompts["comprehensive"])
            base_tokens = len(token_encoder.encode(base_prompt))
            
            # 计算可用于分析结果的token数（保留安全边距）
            max_context_tokens = 120000  # 128K的安全范围
            reserved_tokens = 8000  # 为response和其他内容预留
            available_tokens = max_context_tokens - base_tokens - reserved_tokens
            
            print(f"🔍 [Token管理] 基础提示: {base_tokens} tokens, 可用空间: {available_tokens} tokens")
            
            # 智能选择和压缩分析结果 - 强制限制token数量
            # 无论何种情况，都要严格控制传递给LLM的内容大小
            
            # 预先压缩所有分析结果
            compressed_analyses = []
            for analysis in successful_analyses:
                chunk_id = analysis.get("chunk_id", "unknown")
                analysis_content = analysis.get("analysis", "")
                
                # 强制限制每个分析结果的长度
                max_analysis_length = 2000  # 每个分析结果最多2000字符
                if len(analysis_content) > max_analysis_length:
                    compressed_content = analysis_content[:max_analysis_length-100] + "\\n\\n[已压缩，原长度:" + str(len(analysis_content)) + "字符]"
                else:
                    compressed_content = analysis_content
                
                compressed_analyses.append({
                    "chunk_id": chunk_id,
                    "analysis": compressed_content,
                    "original_length": len(analysis_content)
                })
            
            print(f"🔧 [内容压缩] 已压缩 {len(compressed_analyses)} 个分析结果")
            
            # 分层总结策略 - 始终使用，确保不会超限
            print(f"🔄 [分层总结] 采用强制分层总结策略")
            
            # 第一层：将分块分组并总结每组（严格控制组大小）
            group_size = 2  # 减少到每组2个分块，进一步降低风险
            group_summaries = []
            
            for i in range(0, len(compressed_analyses), group_size):
                group = compressed_analyses[i:i + group_size]
                
                # 构建组内容，严格控制大小
                group_items = []
                total_group_length = 0
                max_group_length = 4000  # 每组最多4000字符
                
                for analysis in group:
                    chunk_id = analysis.get("chunk_id", "unknown")
                    analysis_content = analysis.get("analysis", "")
                    
                    # 检查添加这个分析是否会超限
                    item_text = f"\\n=== 分块 {chunk_id} ===\\n{analysis_content}"
                    if total_group_length + len(item_text) > max_group_length:
                        # 如果会超限，进一步裁剪
                        remaining_space = max_group_length - total_group_length - 50
                        if remaining_space > 100:
                            truncated_content = analysis_content[:remaining_space] + "..."
                            item_text = f"\\n=== 分块 {chunk_id} ===\\n{truncated_content}"
                        else:
                            break  # 空间不够，跳过这个分析
                    
                    group_items.append(item_text)
                    total_group_length += len(item_text)
                
                group_text = "".join(group_items)
                
                # 生成组总结（使用简化提示）
                group_prompt = f"""总结以下分析内容的核心要点（关于：{query}）：

{group_text}

请用简洁语言提取关键信息："""
                
                # 检查组提示的token数量
                group_tokens = len(token_encoder.encode(group_prompt))
                print(f"  📊 [组 {len(group_summaries)+1}] 提示tokens: {group_tokens}")
                
                if group_tokens > 15000:  # 如果组提示超过15K tokens，进一步压缩
                    print(f"  ⚠️ [组 {len(group_summaries)+1}] 提示过长，进一步压缩")
                    # 使用极简版本
                    short_summaries = []
                    for analysis in group:
                        analysis_content = analysis.get("analysis", "")
                        short_summary = analysis_content[:500] + "..." if len(analysis_content) > 500 else analysis_content
                        short_summaries.append(short_summary)
                    
                    group_prompt = f"""总结关键信息（{query}）：
{chr(10).join(short_summaries)}
请简要概括："""
                
                try:
                    group_response = await llm_gen.ainvoke([HumanMessage(content=group_prompt)])
                    group_summaries.append({
                        "group_id": len(group_summaries),
                        "summary": group_response.content,
                        "chunk_count": len(group)
                    })
                    print(f"  ✅ [组 {len(group_summaries)}] 完成，包含 {len(group)} 个分块")
                except Exception as e:
                    print(f"  ❌ [组总结] 失败: {e}")
                    # 如果组总结失败，使用极简版本
                    simplified_summary = f"组{len(group_summaries)}关键信息：" + "；".join([
                        analysis.get("analysis", "")[:200] for analysis in group
                    ])
                    group_summaries.append({
                        "group_id": len(group_summaries),
                        "summary": simplified_summary,
                        "chunk_count": len(group)
                    })
            
            # 第二层：总结所有组总结（严格控制最终总结的大小）
            print(f"📋 [最终总结] 准备总结 {len(group_summaries)} 个组的结果")
            
            # 预先压缩所有组总结
            compressed_group_summaries = []
            total_final_length = 0
            max_final_length = 8000  # 最终总结输入最多8000字符
            
            for group_summary in group_summaries:
                group_id = group_summary['group_id']
                summary_content = group_summary['summary']
                chunk_count = group_summary['chunk_count']
                
                # 为每个组总结分配空间
                max_group_summary_length = max_final_length // len(group_summaries)
                max_group_summary_length = min(max_group_summary_length, 1500)  # 每个组最多1500字符
                
                if len(summary_content) > max_group_summary_length:
                    compressed_content = summary_content[:max_group_summary_length-50] + "..."
                else:
                    compressed_content = summary_content
                
                item_text = f"组{group_id}({chunk_count}块): {compressed_content}"
                
                if total_final_length + len(item_text) <= max_final_length:
                    compressed_group_summaries.append(item_text)
                    total_final_length += len(item_text)
                else:
                    # 如果空间不够，使用极简版本
                    remaining_space = max_final_length - total_final_length - 20
                    if remaining_space > 50:
                        mini_content = summary_content[:remaining_space] + "..."
                        compressed_group_summaries.append(f"组{group_id}: {mini_content}")
                    break
            
            # 构建最终提示（使用简化的基础提示）
            simple_base_prompt = f"""基于以下分组分析结果，回答查询"{query}"：

"""
            
            final_summaries_text = "\\n".join(compressed_group_summaries)
            final_prompt = f"""{simple_base_prompt}{final_summaries_text}

请提供综合回答："""
            
            # 最后检查token数（绝对保证不超限）
            final_tokens = len(token_encoder.encode(final_prompt))
            print(f"🔍 [Token检查] 最终提示: {final_tokens} tokens")
            
            if final_tokens > 15000:  # 如果超过15K tokens，进一步强制压缩
                print(f"🚨 [紧急压缩] 最终提示过长，执行强制压缩")
                
                # 使用最简版本
                ultra_compressed = []
                for i, group_summary in enumerate(group_summaries):
                    summary_content = group_summary['summary']
                    # 每个组只保留前300字符
                    ultra_short = summary_content[:300] + "..." if len(summary_content) > 300 else summary_content
                    ultra_compressed.append(f"{i+1}. {ultra_short}")
                
                final_prompt = f"""回答查询"{query}"，基于以下要点：

{chr(10).join(ultra_compressed)}

综合回答："""
                
                final_tokens = len(token_encoder.encode(final_prompt))
                print(f"🔍 [压缩后] 最终提示: {final_tokens} tokens")
            
            # 确保绝对安全
            if final_tokens > 20000:
                print(f"🚨 [极限压缩] 仍然过长，使用极简模式")
                # 只保留前几个组的核心信息
                essential_info = []
                for i, group_summary in enumerate(group_summaries[:3]):  # 只取前3组
                    summary_content = group_summary['summary']
                    essential = summary_content[:200]  # 每组只要200字符
                    essential_info.append(essential)
                
                final_prompt = f"""关于"{query}"的核心信息：
{chr(10).join(essential_info)}
请简要回答："""
            
            print(f"🤖 [最终调用] 调用LLM，提示长度: {len(final_prompt)} 字符")
            
            response = await llm_gen.ainvoke([HumanMessage(content=final_prompt)])
            
            print(f"✅ [结果总结] 强制分层总结完成")
            
            result = {
                "method": "summary_chunk_results",
                "query": query,
                "summary_focus": summary_focus,
                "total_chunks_analyzed": len(successful_analyses),
                "final_summary": response.content,
                "processing_mode": "forced_hierarchical_summary",
                "group_count": len(group_summaries),
                "original_analysis_count": len(chunk_analyses),
                "successful_analysis_count": len(successful_analyses),
                "compression_applied": True,
                "final_prompt_tokens": final_tokens,
                "success": True
            }
            
            return json.dumps(result, ensure_ascii=False, default=str)
            
        except Exception as e:
            print(f"❌ [结果总结] 总结失败: {e}")
            return json.dumps({
                "method": "summary_chunk_results",
                "error": str(e),
                "success": False
            }, ensure_ascii=False, default=str)
    tools = [
        # 书本管理工具（优先级最高）
        list_available_books_tool,
        add_book_tool,
        switch_book_tool,
        get_current_book_tool,
        
        #=== 新增的RAG检索分离工具 ===
        global_search_retrieve_tool,
        # global_search_generate_tool,
        local_search_retrieve_tool,
        local_search_generate_tool,
        
        #=== 新增：独立LLM调用工具 ===
        llm_generate_tool,
        llm_analyze_tool,
        
        #=== 新增：分块处理工具 ===
        parallel_chunk_analysis_tool,
        summary_chunk_results_tool,
        
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

async def main() -> None:
    graph_agent = GraphAnalysisAgent(use_multi_book=True)

    # 自动加载所有可用的书本
    print("📚 正在自动加载所有可用的书本...")
    
    # 定义要加载的书本列表
    books_to_load = [
        ("book4", "./book4/output"),
        ("book5", "./book5/output"), 
        ("book6", "./book6/output"),
        ("book2", "./rag_book2/ragtest/output"),
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

import os
import json
import asyncio
import random
from typing import List, Dict
from datetime import datetime
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import AzureChatOpenAI

# 使用与您提供的回答agent相同的API配置
api_key = os.getenv("AZURE_OPENAI_API_KEY") or ""

class DuneTopicGenerator:
    def __init__(self):
        self.llm = self._init_azure_llm()
        self.prompt_template = """
        # 角色：科幻小说专家，专注《沙丘》系列
        # 任务：生成与《沙丘》相关的多样化主题和起始问题
        # 要求：
        # 1. 主题必须是《沙丘》小说相关的核心领域
        #    - 世界观设定 (如：香料经济学、弗瑞曼文化)
        #    - 人物关系 (如：厄崔迪与哈克南家族的恩怨)
        #    - 关键情节 (如：保罗成为穆阿迪布的旅程)
        #    - 哲学主题 (如：权力、预知能力或生态责任感)
        #    - 技术创新 (如：防护罩、悬浮车)
        #    - 未解之谜 (如：贝尼·杰瑟里特的长远计划)
        # 2. 严格使用以下JSON格式：
        {{"topic": "主题名称", "question": "起始问题"}}
        # 3. 主题必须能支持多轮对话
        """
    
    def _init_azure_llm(self) -> AzureChatOpenAI:
        return AzureChatOpenAI(
            openai_api_version="2024-12-01-preview",
            azure_deployment="gpt-4o",
            model_name="gpt-4o",
            openai_api_key=api_key,
            azure_endpoint="https://tcamp.openai.azure.com/",
            temperature=0.85,
            max_tokens=800
        )
    
    async def generate_topic(self) -> dict:
        """生成对话主题和起始问题（修复版）"""
        from langchain.schema import HumanMessage, SystemMessage
        
        try:
            # 创建符合要求的消息结构
            messages = [
                SystemMessage(content=self.prompt_template),
                HumanMessage(content="请按照要求生成一个关于《沙丘》的主题和起始问题")
            ]
            
            # 使用正确的invoke方法
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()
            
            # 调试输出
            print(f"🌀 原始响应内容: \n{content}\n{'-'*60}")
            
            # 灵活提取JSON内容
            json_content = None
            
            # 场景1: 包含JSON代码块
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            
            # 场景2: 包含纯JSON
            elif "{" in content and "}" in content:
                json_str = content[content.find("{"):content.rfind("}")+1]
            
            # 场景3: 无JSON标记但格式正确
            elif content.startswith("{") and content.endswith("}"):
                json_str = content
            
            # 尝试解析找到的JSON
            if json_str:
                try:
                    json_content = json.loads(json_str)
                    print(f"✅ JSON解析成功: {json_content}")
                    return json_content
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON解析失败: {str(e)}")
            
            # 直接模式：尝试解析整个响应
            try:
                json_content = json.loads(content)
                print(f"✅ 直接JSON解析成功: {json_content}")
                return json_content
            except:
                pass
            
            # 最终格式处理：键值对提取
            print("⚠️ 无法直接解析为JSON，尝试键值提取...")
            return self._extract_key_values(content)
            
        except Exception as e:
            print(f"⚠️ 主题生成失败: {str(e)}")
            return self._fallback_topic()
    
    def _extract_key_values(self, text: str) -> dict:
        """从非结构化文本提取键值"""
        topic_keywords = ["主题", "话题", "题名", "topic"]
        question_keywords = ["问题", "起始", "question"]
        
        result = {"topic": "", "question": ""}
        lines = text.strip().split("\n")
        
        # 第一遍: 关键词定位
        for line in lines:
            lower_line = line.lower()
            for key in topic_keywords:
                if key in lower_line:
                    result["topic"] = line.split(":", 1)[-1].strip()
            for key in question_keywords:
                if key in lower_line:
                    result["question"] = line.split(":", 1)[-1].strip()
        
        # 第二遍: 提取核心内容
        if not result["topic"]:
            topic_candidates = [line for line in lines if not any(qk in line for qk in question_keywords)]
            if topic_candidates:
                result["topic"] = topic_candidates[0].strip()
        
        if not result["question"]:
            question_candidates = [line for line in lines if "?" in line or "？" in line]
            if question_candidates:
                result["question"] = question_candidates[0].strip()
        
        # 默认情况处理
        if not result["topic"]:
            result["topic"] = "沙丘世界设定"
        if not result["question"]:
            result["question"] = "请解释香料在沙丘宇宙中的重要性"
        
        print(f"🔍 提取结果: {result}")
        return result
    
    def _fallback_topic(self) -> dict:
        """备用主题列表（扩展版）"""
        topics = [
            {"topic": "香料经济学", "question": "香料在沙丘宇宙中的经济和政治意义是什么？"},
            {"topic": "保罗的预知能力", "question": "保罗的预知能力如何塑造他的命运决策？"},
            {"topic": "弗瑞曼人文化与生态观", "question": "弗瑞曼人如何适应阿拉基斯的极端环境并发展出独特文化？"},
            {"topic": "贝尼·杰瑟里特姐妹会的权谋", "question": "贝尼·杰瑟里特姐妹会的繁殖计划目标和实施策略是什么？"},
            {"topic": "哈克南与厄崔迪家族的世仇", "question": "哈克南家族与厄崔迪家族的争斗如何影响沙丘宇宙的政治格局？"},
            {"topic": "沙虫生态系统", "question": "沙虫在阿拉基斯生态系统中的角色有什么独特性？"},
            {"topic": "门塔特计算技术", "question": "门塔特的计算能力在沙丘宇宙中有哪些应用和局限？"},
            {"topic": "沙丘中的水伦理", "question": "水在弗瑞曼文化中的象征意义和实际价值是什么？"}
        ]
        return random.choice(topics)


class DuneFollowUpGenerator:
    """根据对话历史生成后续问题"""
    def __init__(self):
        self.llm = self._init_azure_llm()
        self.prompt_template = """
        # 角色：科幻小说专家，专注《沙丘》系列
        # 任务：基于对话历史提出自然连贯的后续问题
        #
        # 当前对话主题：{topic}
        # 最新回答摘要：{answer_summary}
        # 
        # 要求：
        # 1. 问题必须与主题({topic})紧密相关
        # 2. 应基于最新回答中的信息继续深入
        # 3. 可以是澄清、扩展或挑战性提问
        # 4. 输出：单一问题（不带任何其他文本）
        """
        
    def _init_azure_llm(self) -> AzureChatOpenAI:
        return AzureChatOpenAI(
            openai_api_version="2024-12-01-preview",
            azure_deployment="gpt-4o",
            model_name="gpt-4o",
            azure_endpoint="https://tcamp.openai.azure.com/",
            openai_api_key=api_key,
            temperature=0.7,
            max_tokens=500
        )
    
    async def generate_followup(
        self, 
        topic: str, 
        last_answer: str
    ) -> str:
        """生成基于上下文的后续问题"""
        try:
            # 创建问题摘要确保不超长
            summary = last_answer[:1500] if len(last_answer) > 1500 else last_answer
            prompt = PromptTemplate(
                template=self.prompt_template,
                input_variables=["topic", "answer_summary"]
            )
            
            chain = LLMChain(llm=self.llm, prompt=prompt)
            response = await chain.ainvoke({
                "topic": topic,
                "answer_summary": summary
            })
            
            return response.get('text', '').strip().strip('"').strip("'")
        except Exception as e:
            print(f"⚠️ 后续问题生成失败: {str(e)}，使用基础问题")
            return self._fallback_question(topic)
    
    def _fallback_question(self, topic: str) -> str:
        """备用问题的通用模式"""
        questions = [
            f"关于{topic}，请提供更多细节？",
            f"你能更详细地解释这个话题:{topic}的某个方面吗？",
            f"在{topic}的背景下，还有什么重要因素需要考虑？",
            f"在讨论{topic}时，常见的争议点是什么？"
        ]
        return random.choice(questions)

class RequestLogger:
    """增强型请求日志系统"""
    def __init__(self):
        self.logs = []
    
    def log(self, entry: dict):
        """记录带时间戳的日志项"""
        entry["timestamp"] = datetime.now().isoformat()
        self.logs.append(entry)
        
        # 当日志积压过大时自动清理
        if len(self.logs) > 100:
            self.logs = self.logs[-50:]
    
    def analyze_failures(self):
        """分析失败模式"""
        failures = [log for log in self.logs if log["status"] == "failure"]
        
        if not failures:
            return "无失败记录"
        
        # 统计常见错误类型
        error_counts = {}
        for f in failures:
            error_type = f["error"].split(":")[0]  # 取错误类型前缀
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # 生成分析报告
        report = f"### 过去{len(failures)}次失败请求分析\n"
        report += "常见错误类型：\n"
        for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
            report += f"- {error}: {count}次\n"
        
        # 最后5条错误详情
        report += "\n最近失败详情：\n"
        for f in failures[-5:]:
            report += f"{f['timestamp']} [{f['strategy']}]: {f['error']}\n"
        
        return report


import json
from datetime import datetime
import random

class InteractiveDialogueSystem:
    """简化版主题导向多轮对话系统，仅保留核心交互和存储功能"""
    def __init__(self, graph_agent):
        # 初始化核心组件
        self.topic_gen = DuneTopicGenerator()
        self.followup_gen = DuneFollowUpGenerator()
        self.dialogues = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.agent_executor = create_graphrag_agent(graph_agent)
    
    async def run_conversation(self):
        """执行一个连贯主题的对话（简化版）"""
        # 生成主题和起始问题
        topic_data = await self.topic_gen.generate_topic()
        topic = topic_data["topic"]
        current_question = topic_data["question"]
        
        conversation = []
        print(f"\n{'=' * 50}")
        print(f"🏁 启动新对话 | 主题: {topic}")
        print(f"⚡ 起始问题: {current_question}")
        print(f"{'=' * 50}")
        
        # 确定对话轮次 (4-6轮)
        max_turns = random.randint(4, 6)
        
        for turn in range(max_turns):
            # 获取回答
            answer_data = await self.agent_executor.ainvoke({
                "input": current_question
            })
            
            # 显示回答
            print("\n--- Agent 回答 ---")
            print(answer_data.get("output"))
            print("--------------------\n")
            answer = answer_data.get("output")
            
            # 存储当前轮次
            conversation.append({
                "turn": turn,
                "question": current_question,
                "answer": answer
            })
            
            # 如果是最后一轮则停止
            if turn == max_turns - 1:
                break
            
            # 生成后续问题
            current_question = await self.followup_gen.generate_followup(
                topic=topic,
                last_answer=answer
            )
            print(f"🔍 生成后续问题: {current_question}")
        
        # 存储完整对话
        self.store_conversation(topic, conversation)
        print(f"✅ 主题 '{topic}' 完成 | 轮次: {len(conversation)}")
    
    def store_conversation(self, topic: str, conversation: list):
        """存储对话到内存数据集"""
        self.dialogues.append({
            "session": f"{self.session_id}_{len(self.dialogues)+1}",
            "topic": topic,
            "conversation": conversation,
            "created_at": datetime.now().isoformat()
        })
    
    def save_to_jsonl(self, filename: str = "dune_themed_dialogues.jsonl"):
        """保存所有对话到JSONL文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            for dialogue in self.dialogues:
                # 创建精简结构
                clean_entry = {
                    "session": dialogue["session"],
                    "topic": dialogue["topic"],
                    "created_at": dialogue["created_at"],
                    "conversation": dialogue["conversation"]
                }
                f.write(json.dumps(clean_entry, ensure_ascii=False) + '\n')
        print(f"💾 已保存 {len(self.dialogues)} 个对话到 {filename}")


async def main():
    # 1. 先初始化 GraphAnalysisAgent
    graph_agent = GraphAnalysisAgent(use_multi_book=True)
    
    # 2. 增强知识库加载逻辑
    book_path = "./rag/output"
    if os.path.exists(book_path):
        print(f"📚 找到知识库路径: {book_path}")
        
        # 检查必要文件
        required_files = ["communities.parquet", "entities.parquet", 
                          "community_reports.parquet", "relationships.parquet"]
        
        missing_files = [f for f in required_files 
                        if not os.path.exists(os.path.join(book_path, f))]
        
        if missing_files:
            print(f"⚠️ 知识库不完整，缺少文件: {', '.join(missing_files)}")
            print("⚠️ 将从在线源补充知识库...")
            
            # 从在线知识源补充基础知识
            try:
                await graph_agent.global_search_full_async("沙丘世界基础设定")
            except Exception as e:
                print(f"⛔ 知识库补充失败: {e}")
        else:
            graph_agent.add_book("dune_default", book_path)
            graph_agent.switch_book("dune_default")
            print("✅ 知识库加载成功")
            
            # 测试连接
            try:
                await graph_agent.global_search_full_async("测试连接")
                print("✅ 知识库连接正常")
            except Exception as e:
                print(f"⛔ 知识库连接异常: {e}")
    else:
        print("⚠️ 默认知识库路径不存在")
    
    # 3. 将 graph_agent 传递给 InteractiveDialogueSystem
    dialogue_system = InteractiveDialogueSystem(graph_agent)
    
    # 4. 执行多个主题的对话
    num_conversations = 1
    print(f"\n🚀 开始生成 {num_conversations} 个主题的多轮对话...")
    
    for i in range(num_conversations):
        await dialogue_system.run_conversation()
        if i < num_conversations - 1:
            print("\n" + "="*50)
            print(f"⚡ 准备下一对话 ({i+1}/{num_conversations})")
            print("="*50)
    
    # 5. 打印统计报告并保存结果
    dialogue_system.print_stats_report()
    dialogue_system.save_to_jsonl()
    print("✅ 所有对话完成并保存！")

if __name__ == "__main__":
    asyncio.run(main())
