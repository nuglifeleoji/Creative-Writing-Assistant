import pandas as pd
import json
from typing import List, Dict, Any
from openai import OpenAI
import os
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY") or "",
    base_url="https://api.siliconflow.cn/v1",
    timeout=60.0  
)

class GraphAnalysisAgent:
    def __init__(self):
        self.graph_data = {}
        self.load_graph_data()
        
    def load_graph_data(self):
        """加载GraphRAG生成的所有数据"""
        self.graph_data['entities'] = pd.read_parquet('output/entities.parquet')
        self.graph_data['relationships'] = pd.read_parquet('output/relationships.parquet')
        self.graph_data['communities'] = pd.read_parquet('output/communities.parquet')
        self.graph_data['text_units'] = pd.read_parquet('output/text_units.parquet')
        self.graph_data['documents'] = pd.read_parquet('output/documents.parquet')
        self.graph_data['community_reports'] = pd.read_parquet('output/community_reports.parquet')
    
    def get_characters(self) -> Dict[str, Any]:
        """获取故事中的人物"""
        entities = self.graph_data['entities']
        people = entities[
            (entities['type'].str.lower() == 'person') |
            (entities['type'] == 'PERSON')
        ]
        characters_list = []
        for _, row in people.iterrows():
            title = str(row['title']) if pd.notna(row['title']) else "未知"
            description = str(row['description']) if pd.notna(row['description']) else "无描述"
            characters_list.append({
                "title": title,
                "description": description[:300] 
            })
        result = {
            "total_characters": len(people),
            "characters": characters_list
        }
        return result
    
    def get_relationships(self, p1: str, p2: str) -> Dict[str, Any]:
        """获取两个特定人物之间的关系"""
        relationships = self.graph_data['relationships']
        entities = self.graph_data['entities']
        people = entities[entities['type'] == 'PERSON']['title'].tolist()
        filtered_relationships = []
        for _, row in relationships.iterrows():
            source = str(row['source']) if pd.notna(row['source']) else ""
            target = str(row['target']) if pd.notna(row['target']) else ""
            description = str(row['description']) if pd.notna(row['description']) else "无描述"
            if (p1 in source and p2 in target) or (p1 in target and p2 in source):
                filtered_relationships.append({
                    "source": source,
                    "target": target,
                    "description": description[:300],
                    "weight": row.get('weight', 0)
                })
        result = {
            "person1": p1,
            "person2": p2,
            "relationships": filtered_relationships,
        }
        return result
    
    def get_important_locations(self) -> Dict[str, Any]:
        """获取故事中的5个重要地点"""
        entities = self.graph_data['entities']
        locations_df = entities[entities['type'] == 'GEO']
        top_locations = locations_df.nlargest(5, 'frequency')
        locations_list = []
        for _, row in top_locations.iterrows():
            locations_list.append({
                "name": row['title'],
                "description": str(row['description'])[:300]
            })
        
        result = {
            "top_5_locations": locations_list
        }
        return result
    def background_knowledge(self) -> Dict[str, Any]:
        """获取故事的背景知识"""
        community_reports = self.graph_data['community_reports']
        reports_list = []
        for _, row in community_reports.iterrows():
            reports_list.append({
                "community_id": str(row.get('id', '')),
                "full_content": str(row.get('full_content', ''))[:500], 
            })
        
        result = {
            "community_reports": reports_list
        }
        return result

available_functions = [
    {
        "type": "function",
        "function": {
            "name": "get_characters",
            "description": "获取故事中的所有人物角色",
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
            "description": "获取两个特定人物之间的关系",
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
            "description": "获取故事中的5个重要地点",
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
            "description": "获取故事的背景知识",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
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
            "content": "你是一个图数据分析助手。你可以获取故事中的人物信息和故事的情节信息。"
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
    test_query = "故事的背景故事是什么？"
    
    print(f"问题: {test_query}")
    try:
        answer = chat_with_agent(test_query)
        print(f"回答: {answer}")
    except Exception as e:
        print(f"错误: {e}")
    print("-" * 50)

if __name__ == "__main__":
    test_agent() 