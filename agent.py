import pandas as pd
import json
import subprocess
import os
from typing import List, Dict, Any
from openai import OpenAI

client = OpenAI(
    api_key="sk-crrrxsgwputbfxhvilcgzafqyrkzevfmcmocyupkbpcivnrh",
    base_url="https://api.siliconflow.cn/v1",
    timeout=60.0  
)

class GraphAnalysisAgent:
    def __init__(self):
        self.rag_root = "./tencent"
        
    def run_graphrag_query(self, method: str, query: str) -> Dict[str, Any]:
        """运行GraphRAG查询"""
        try:
            cmd = [
                "graphrag", "query",
                "--root", self.rag_root,
                "--method", method,
                "--query", query
            ]
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            if result.returncode == 0:
                return {
                    "method": method,
                    "query": query,
                    "result": result.stdout,
                    "success": True
                }
            else:
                return {
                    "method": method,
                    "query": query,
                    "error": result.stderr,
                    "success": False
                }
        except Exception as e:
            return {
                "method": method,
                "query": query,
                "error": f"Command execution failed: {str(e)}",
                "success": False
            }
        
    def get_characters(self) -> Dict[str, Any]:
        query = "列出故事中的所有人物角色"
        return self.run_graphrag_query("global", query)
    
    def get_relationships(self, p1: str, p2: str) -> Dict[str, Any]:
        query = f"分析{p1}和{p2}之间的关系"
        return self.run_graphrag_query("local", query)
    
    def get_important_locations(self) -> Dict[str, Any]:
        query = "分析故事中的重要地点和场景"
        return self.run_graphrag_query("global", query)
    
    def background_knowledge(self) -> Dict[str, Any]:
        query = "分析故事的背景知识和主要情节"
        return self.run_graphrag_query("global", query)
    
    def local_search_query(self, query: str) -> Dict[str, Any]:
        """使用local_search进行自定义查询"""
        return self.run_graphrag_query("local", query)
    
    def global_search_query(self, query: str) -> Dict[str, Any]:
        """使用global_search进行自定义查询"""
        return self.run_graphrag_query("global", query)

available_functions = [
    {
        "type": "function",
        "function": {
            "name": "get_characters",
            "description": "使用local_search获取故事中的所有人物角色",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_relationships",
            "description": "使用local_search获取两个特定人物之间的关系",
            "parameters": {
                "type": "object",
                "properties": {
                    "p1": {
                        "type": "string",
                        "description": "第一个人物的名称"
                    },
                    "p2": {
                        "type": "string",
                        "description": "第二个人物的名称"
                    }
                },
                "required": ["p1", "p2"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_important_locations",
            "description": "使用global_search获取故事中的重要地点",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "background_knowledge",
            "description": "使用global_search获取故事的背景知识",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "local_search_query",
            "description": "使用local_search进行自定义查询",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "查询内容"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "global_search_query",
            "description": "使用global_search进行自定义查询",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "查询内容"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

def chat_with_agent(user_query: str):
    """与Agent进行对话"""
    agent = GraphAnalysisAgent()
    
    # 创建消息
    messages = [
        {
            "role": "system",
            "content": "你是一个图数据分析助手。你可以使用GraphRAG的local_search和global_search功能来获取故事中的人物信息、关系信息和背景知识。"
        },
        {
            "role": "user",
            "content": user_query
        }
    ]
    
    print("正在调用LLM...")
    
    # 调用LLM
    response = client.chat.completions.create(
        model="Qwen/QwQ-32B",
        messages=messages,
        tools=available_functions,
        tool_choice="auto"
    )
    
    # 处理响应
    response_message = response.choices[0].message
    
    # 如果有函数调用
    if response_message.tool_calls:
        # 执行函数调用
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if function_name == "get_characters":
                result = agent.get_characters()
            elif function_name == "get_relationships":
                result = agent.get_relationships(function_args["p1"], function_args["p2"])
            elif function_name == "get_important_locations":
                result = agent.get_important_locations()
            elif function_name == "background_knowledge":
                result = agent.background_knowledge()
            elif function_name == "local_search_query":
                result = agent.local_search_query(function_args["query"])
            elif function_name == "global_search_query":
                result = agent.global_search_query(function_args["query"])
            else:
                result = {"error": f"未知函数: {function_name}"}
            
            # 将结果添加到消息中
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False)
            })
        
        # 再次调用LLM生成最终回答
        final_response = client.chat.completions.create(
            model="Qwen/QwQ-32B",
            messages=messages
        )
        
        return final_response.choices[0].message.content
    else:
        return response_message.content

# 测试函数
def test_agent():
    test_queries = [
        "故事的背景故事是什么？",
        "列出故事中的主要人物",
        "分析弗兰肯斯坦和怪物之间的关系"
    ]
    
    agent = GraphAnalysisAgent()
    
    for test_query in test_queries:
        print(f"问题: {test_query}")
        try:
            answer = chat_with_agent(test_query)
            print(f"回答: {answer}")
        except Exception as e:
            print(f"错误: {e}")
        print("-" * 50)

if __name__ == "__main__":
    test_agent() 