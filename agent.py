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
        return self.run_graphrag_query("local", query)
    
    def global_search_query(self, query: str) -> Dict[str, Any]:
        return self.run_graphrag_query("global", query)

available_functions = [
    {
        "type": "function",
        "function": {
            "name": "get_characters",
            "description": "获取故事中的所有人物角色信息。这是分析故事的基础，必须先调用此函数了解人物。",
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
            "description": "获取故事的背景知识和主要情节。这是理解故事核心内容的关键函数，必须调用。",
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
    agent = GraphAnalysisAgent()
    messages = [
        {
            "role": "system",
            "content": "你是一个专业的文学分析助手。当用户询问关于故事内容时，你必须严格按照以下步骤执行：\n\n⚠️ 强制要求：在回答任何关于故事内容的问题之前，你必须先调用以下函数来获取信息！\n\n1. 首先调用 get_characters() 获取所有人物信息\n2. 然后调用 background_knowledge() 获取故事背景和主要情节\n3. 最后调用 get_important_locations() 获取重要地点信息\n\n只有在获取了这些基础信息后，你才能进行续写分析。\n\n函数调用顺序：\n- get_characters() - 必须首先调用\n- background_knowledge() - 必须其次调用\n- get_important_locations() - 必须最后调用\n- get_relationships(p1, p2) - 可选，用于分析特定人物关系\n- local_search_query(query) - 可选，用于具体查询\n- global_search_query(query) - 可选，用于全局查询\n\n获取信息后，基于搜索结果进行深入分析，给出详细的续写建议。"
        },
        {
            "role": "user",
            "content": user_query
        }
    ]
    
    print("正在调用LLM...")
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
        print(f"\n🔧 检测到 {len(response_message.tool_calls)} 个函数调用:")
        
        # 执行函数调用
        for i, tool_call in enumerate(response_message.tool_calls, 1):
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            print(f"\n📞 函数调用 {i}: {function_name}")
            if function_args:
                print(f"   参数: {function_args}")
            
            # 执行函数
            if function_name == "get_characters":
                print("   🎭 正在获取人物信息...")
                result = agent.get_characters()
            elif function_name == "get_relationships":
                print(f"   🔗 正在分析 {function_args.get('p1', '')} 和 {function_args.get('p2', '')} 的关系...")
                result = agent.get_relationships(function_args["p1"], function_args["p2"])
            elif function_name == "get_important_locations":
                print("   🗺️ 正在获取重要地点信息...")
                result = agent.get_important_locations()
            elif function_name == "background_knowledge":
                print("   📚 正在获取背景知识...")
                result = agent.background_knowledge()
            elif function_name == "local_search_query":
                print(f"   🔍 正在执行local_search查询: {function_args.get('query', '')}")
                result = agent.local_search_query(function_args["query"])
            elif function_name == "global_search_query":
                print(f"   🌍 正在执行global_search查询: {function_args.get('query', '')}")
                result = agent.global_search_query(function_args["query"])
            else:
                print(f"   ❌ 未知函数: {function_name}")
                result = {"error": f"未知函数: {function_name}"}
            
            # 显示函数执行结果
            if result.get("success", False):
                print(f"   ✅ 函数执行成功")
                if result.get("result"):
                    print(f"   结果长度: {len(str(result['result']))} 字符")
            else:
                print(f"   ❌ 函数执行失败: {result.get('error', '未知错误')}")
            
            # 将结果添加到消息中
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False)
            })
        
        print(f"\n🤖 所有函数调用完成，正在生成最终回答...")
        
        # 再次调用LLM生成最终回答
        final_response = client.chat.completions.create(
            model="Qwen/QwQ-32B",
            messages=messages
        )
        
        return final_response.choices[0].message.content
    else:
        print("\n⚠️ 警告：LLM没有调用任何函数！")
        print("这表示LLM可能没有按照要求执行必要的搜索步骤。")
        return response_message.content

# 测试函数
def test_agent():
    test_queries = [
        "请续写这本书"
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