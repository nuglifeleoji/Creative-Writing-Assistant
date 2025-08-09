
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
api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY") or ""


from langchain.agents import tool
from langchain.agents import create_react_agent, AgentExecutor, create_tool_calling_agent
from langchain import hub
from langchain_openai import ChatOpenAI,AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate
from search.global_search import global_search as graphrag_global_search
from search.local_search import local_search
import prompt_utils
class GraphAnalysisAgent:
    def __init__(self):
        self.global_search = graphrag_global_search
        self.local_search = local_search
    async def global_search_async(self, query: str) -> Dict[str, Any]:
        return await self.global_search(query)

    async def local_search_async(self, query: str) -> Dict[str, Any]:
        return await self.local_search(query)

    async def get_characters_async(self) -> Dict[str, Any]:
        return await self.global_search_async("列出故事中的所有人物角色")

    async def get_relationships_async(self, p1: str, p2: str) -> Dict[str, Any]:
        return await self.local_search_async(f"分析{p1}和{p2}之间的关系")

    async def get_important_locations_async(self) -> Dict[str, Any]:
        return await self.global_search_async("分析故事中的重要地点和场景")

    async def background_knowledge_async(self) -> Dict[str, Any]:
        return await self.global_search_async("分析故事的背景知识和主要情节")

    async def get_character_profile_async(self, character_name: str) -> Dict[str, Any]:
        return await self.global_search_async(f"获取{character_name}的详细信息")
    
    async def get_main_theme_async(self) -> Dict[str, Any]:
        return await self.global_search_async("分析故事的主题")

    async def get_open_questions_async(self) -> Dict[str, Any]:
        return await self.global_search_async("本书有什么悬念或者没有解决的伏笔？")

    async def get_conflict_matrix_async(self) -> Dict[str, Any]:
        return await self.local_search_async("罗列出角色之间或者不同派系之间的冲突")
    
    async def get_causal_chains_async(self, event: str) -> Dict[str, Any]:
        return await self.local_search_async(f"获取{event}事件的因果链：前置条件→触发→结果→后果")
        

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
        """获取两个特定人物之间的关系（当前用全局查询替代本地查询）。输入参数p1和p2是人物名称。"""
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
    async def get_conflict_matrix_tool() -> str:
        """获取本书的冲突矩阵。"""
        result = await graphrag_agent_instance.get_conflict_matrix_async()
        return json.dumps(result, ensure_ascii=False)
    @tool
    async def get_causal_chains_tool(event: str) -> str:
        """获取给定事件的因果链。"""
        result = await graphrag_agent_instance.get_causal_chains_async(event)
        return json.dumps(result, ensure_ascii=False)
    # 将所有工具放入一个列表中
    tools = [
        get_characters_tool,
        get_relationships_tool,
        get_important_locations_tool,
        background_knowledge_tool,
        local_search_tool,
        global_search_tool,
        get_character_profile_tool,
        get_main_theme_tool,
        get_open_questions_tool,
        get_conflict_matrix_tool,
        get_causal_chains_tool
    ]

    # 初始化 LLM
    # 确保你已经设置了 OPENAI_API_KEY 环境变量
    llm = AzureChatOpenAI(
        openai_api_version="2024-12-01-preview",
        azure_deployment="gpt-4o",
        model_name="gpt-4o",
        azure_endpoint="https://tcamp.openai.azure.com/",
        openai_api_key=api_key,
        temperature=0.3
    )


    prompt = f"""
    You are a helpful assistant that can answer questions about the data in the tables provided.

    ---Goal---
你是一个智能创作助手，可以进行信息分析和探索，通过系统性的调查来完成复杂的创作任务。
## 历史对话
历史对话信息
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

    while True:
        user_query = input("\n请输入你的问题：")
        if user_query.lower() == 'exit':
            break

        try:
            # 使用异步调用，匹配异步工具
            response = await agent_executor.ainvoke({"input": user_query, "guidelines": prompt_utils.build_guidelines(), "functions": agent_executor.tools, "requirements": prompt_utils.build_requirements(), "response_format": prompt_utils.build_response_format()})
            print("\n--- Agent 回答 ---")
            print(response.get("output"))
            print("--------------------\n")
        except Exception as e:
            print(f"发生错误：{e}")
            break


if __name__ == "__main__":
    asyncio.run(main())
