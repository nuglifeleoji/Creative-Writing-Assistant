import os
import subprocess
import json
from typing import Dict, Any

# 确保你已经安装了以下库
# pip install langchain langchain-openai

# 注意配置OPENAI_API_KEY以及graphrag所在路径(代码第172行)

from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")



from langchain.agents import tool
from langchain.agents import create_react_agent, AgentExecutor, create_tool_calling_agent
from langchain import hub
from langchain_openai import ChatOpenAI,AzureChatOpenAI

# --- 第一步：封装 GraphRAG 查询的后端 ---
# 这部分直接采用了你提供的代码，用于执行 GraphRAG 命令行查询
class GraphAnalysisAgent:
    def __init__(self, rag_root: str):
        self.rag_root = rag_root

    def run_graphrag_query(self, method: str, query: str) -> Dict[str, Any]:
        """通过命令行运行 GraphRAG 查询，并返回结果。"""
        try:
            cmd = [
                "graphrag", "query",
                "--root", self.rag_root,
                "--method", method,
                "--query", query
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
                check=True
            )
            
            return {
                "method": method,
                "query": query,
                "result": result.stdout,
                "success": True
            }
        except subprocess.CalledProcessError as e:
            return {
                "method": method,
                "query": query,
                "error": e.stderr,
                "success": False
            }
        except Exception as e:
            return {
                "method": method,
                "query": query,
                "error": f"命令执行失败: {str(e)}",
                "success": False
            }

    def get_characters(self) -> Dict[str, Any]:
        """获取故事中的所有人物角色。"""
        query = "列出故事中的所有人物角色"
        return self.run_graphrag_query("global", query)
    
    def get_relationships(self, p1: str, p2: str) -> Dict[str, Any]:
        """获取两个特定人物之间的关系。"""
        query = f"分析{p1}和{p2}之间的关系"
        return self.run_graphrag_query("local", query)
    
    def get_important_locations(self) -> Dict[str, Any]:
        """获取故事中的重要地点。"""
        query = "分析故事中的重要地点和场景"
        return self.run_graphrag_query("global", query)
    
    def background_knowledge(self) -> Dict[str, Any]:
        """获取故事的背景知识和主要情节。"""
        query = "分析故事的背景知识和主要情节"
        return self.run_graphrag_query("global", query)
    
    def local_search_query(self, query: str) -> Dict[str, Any]:
        """进行自定义 local_search 查询。"""
        return self.run_graphrag_query("local", query)
    
    def global_search_query(self, query: str) -> Dict[str, Any]:
        """进行自定义 global_search 查询。"""
        return self.run_graphrag_query("global", query)

# --- 第二步：创建 LangChain Agent ---
def create_graphrag_agent(graphrag_agent_instance: GraphAnalysisAgent) -> AgentExecutor:
    """
    创建并返回一个可以调用 GraphRAG 命令行功能的 LangChain Agent。
    """
    # 使用 @tool 装饰器，将 GraphAnalysisAgent 的方法包装成 LangChain 工具
    # 注意：这里的工具函数需要能够被 Agent 直接调用，所以我们使用闭包来传递实例
    @tool
    def get_characters_tool() -> str:
        """使用 GraphRAG 的全局查询功能获取故事中的所有人物角色。"""
        result = graphrag_agent_instance.get_characters()
        return json.dumps(result, ensure_ascii=False)

    @tool
    def get_relationships_tool(p1: str, p2: str) -> str:
        """使用 GraphRAG 的局部查询功能，获取两个特定人物之间的关系。输入参数p1和p2是人物名称。"""
        result = graphrag_agent_instance.get_relationships(p1, p2)
        return json.dumps(result, ensure_ascii=False)

    @tool
    def get_important_locations_tool() -> str:
        """使用 GraphRAG 的全局查询功能获取故事中的重要地点。"""
        result = graphrag_agent_instance.get_important_locations()
        return json.dumps(result, ensure_ascii=False)

    @tool
    def background_knowledge_tool() -> str:
        """使用 GraphRAG 的全局查询功能获取故事的背景知识。"""
        result = graphrag_agent_instance.background_knowledge()
        return json.dumps(result, ensure_ascii=False)
    
    @tool
    def local_search_tool(query: str) -> str:
        """使用 GraphRAG 的局部查询功能进行自定义搜索。输入是一个字符串形式的查询。"""
        result = graphrag_agent_instance.local_search_query(query)
        return json.dumps(result, ensure_ascii=False)

    @tool
    def global_search_tool(query: str) -> str:
        """使用 GraphRAG 的全局查询功能进行自定义搜索。输入是一个字符串形式的查询。"""
        result = graphrag_agent_instance.global_search_query(query)
        return json.dumps(result, ensure_ascii=False)

    # 将所有工具放入一个列表中
    tools = [
        get_characters_tool,
        get_relationships_tool,
        get_important_locations_tool,
        background_knowledge_tool,
        local_search_tool,
        global_search_tool
    ]

    # 初始化 LLM
    # 确保你已经设置了 OPENAI_API_KEY 环境变量
    llm = AzureChatOpenAI(
        openai_api_version="2024-12-01-preview",
        azure_deployment="gpt-4o-mini",
        model_name="gpt-4o-mini",
        azure_endpoint="https://tcamp.openai.azure.com/",  # 👈 将 openai_api_base 替换为 azure_endpoint
        openai_api_key=api_key,
        temperature=0.3
    )

    # 从 LangChain Hub 获取 ReAct 提示模板
    prompt = hub.pull("hwchase17/openai-tools-agent")

    # 创建 Agent
    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)

    # 创建 Agent 执行器
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

# --- 主程序入口 ---
if __name__ == "__main__":
    # 初始化你的 GraphAnalysisAgent，传入 GraphRAG 项目的根目录
    graph_agent = GraphAnalysisAgent(rag_root="/home/grass8cow/qcd")

    # 使用这个实例创建 LangChain Agent
    agent_executor = create_graphrag_agent(graph_agent)

    print("LangChain Agent with GraphRAG CLI tools is ready. Type 'exit' to quit.")
    
    while True:
        user_query = input("\n请输入你的问题：")
        if user_query.lower() == 'exit':
            break
        
        try:
            # 调用 Agent 执行器
            response = agent_executor.invoke({"input": user_query})
            print("\n--- Agent 回答 ---")
            print(response["output"])
            print("--------------------\n")
        except Exception as e:
            print(f"发生错误：{e}")
            break