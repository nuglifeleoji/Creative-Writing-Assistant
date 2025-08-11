from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import asyncio
import json
import os
import queue
import threading
import time
import uuid
from langchain_agent import GraphAnalysisAgent
from langchain.callbacks.base import BaseCallbackHandler
from typing import Any, Dict, List
from langchain_core.agents import AgentAction, AgentFinish

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局变量
graph_agent = None
graph_agent_instance = None  # 保存 GraphAnalysisAgent 实例的引用

# 线程安全的回调消息队列
callback_queue = queue.Queue()
class StreamingCallbackHandler(BaseCallbackHandler):
    """只暴露过程，不泄露推理细节（不输出 action.log）。"""
    def __init__(self, yield_func):
        self.yield_func = yield_func
        self.current_tool = None
        self._tool_start_ts = {}
        self._run_id = str(uuid.uuid4())
        self._sent_events = set()  # 用于去重

    def _send(self, etype: str, payload: Dict[str, Any]):
        # 对于token事件，不进行去重（因为每个token都不同）
        if etype == "llm_token":
            # 直接跳过token事件，避免前端显示过多无用信息
            return
            
        # 对于其他事件，使用事件类型+关键内容进行去重
        if etype in ["run_start", "run_end"]:
            event_key = f"{etype}"  # 这些事件每次只应该发送一次
        else:
            event_key = f"{etype}:{str(payload)[:50]}"
        
        if event_key in self._sent_events:
            print(f"⚠️ 跳过重复事件: {etype}")
            return
        
        self._sent_events.add(event_key)
        payload = {"runId": self._run_id, **payload}
        # 按 SSE 标准写法输出：event + data + 空行
        sse_message = f"event: {etype}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        print(f"🔄 回调发送SSE: {etype} -> {str(payload)[:100]}...")
        self.yield_func(sse_message)

    # 任务起止
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        self._send("run_start", {
            "chain": serialized.get("name", "chain"),
            "inputsPreview": str(inputs)[:300]
        })

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        self._send("run_end", {
            "outputsPreview": str(outputs)[:300]
        })

    # Agent 决策（不输出思维文本）
    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        self._send("plan", {
            "nextTool": action.tool,
            "argsPreview": str(action.tool_input)[:300]
        })

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> Any:
        self._send("plan_done", {
            "finalReturnPreview": str(finish.return_values)[:300]
        })

    # 工具调用
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        tool_name = serialized.get("name", "unknown_tool")
        self.current_tool = tool_name
        self._tool_start_ts[tool_name] = time.time()
        self._send("tool_start", {
            "tool": tool_name,
            "inputPreview": input_str[:500]
        })

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        tool = self.current_tool or 'unknown_tool'
        latency = None
        if tool in self._tool_start_ts:
            latency = round((time.time() - self._tool_start_ts.pop(tool)), 3)
        self._send("tool_end", {
            "tool": tool,
            "latencySec": latency,
            "outputPreview": output[:800],
            "truncated": len(output) > 800
        })

    # LLM token 流 + 用量
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        self._send("llm_start", {
            "model": serialized.get("name", "llm"),
            "promptPreview": (prompts[0][:300] if prompts else "")
        })

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        self._send("llm_token", {"token": token})

    def on_llm_end(self, response, **kwargs: Any) -> None:
        usage = {}
        try:
            usage = getattr(response, "usage_metadata", None) or {}
            if not usage and hasattr(response, "generations"):
                gi = response.generations[0][0].generation_info or {}
                usage = gi.get("usage", gi)
        except Exception:
            usage = {}
        self._send("llm_end", {"usage": usage})

def initialize_agent():
    """初始化LangChain代理"""
    global graph_agent, graph_agent_instance
    try:
        # 创建 GraphAnalysisAgent 实例
        graph_agent_instance = GraphAnalysisAgent(use_multi_book=True)
        
        # 自动加载所有可用的书本
        print("📚 正在自动加载所有可用的书本...")
        
        # 定义要加载的书本列表
        books_to_load = [
            ("平凡的世界", "./book4/output"),
            ("三体", "./book5/output"), 
            ("三体2", "./book6/output"),
            ("超新星纪元", "./cxx/output"),
            ("白夜行", "./rag_book2/ragtest/output"),
            ("弗兰肯斯坦", "./tencent/output"),
            ("沙丘", "./rag/output"),
            ("嫌疑人x的献身", "./book7/output"),
            ("斗罗大陆4", "./book8/output"),
            ("三国演义","./sanguo/output")
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
                        graph_agent_instance.add_book(book_name, book_path)
                        loaded_books.append(book_name)
                        print(f"✅ 成功加载书本: {book_name} -> {book_path}")
                    else:
                        print(f"⚠️ 跳过 {book_name}: 缺少必要文件 {missing_files}")
                else:
                    print(f"⚠️ 跳过 {book_name}: 路径不存在 {book_path}")
            except Exception as e:
                print(f"❌ 加载 {book_name} 失败: {e}")
        
        print(f"✅ 总共加载了 {len(loaded_books)} 本书: {', '.join(loaded_books)}")
        
        # 不自动选择书本，让用户主动选择
        if loaded_books:
            print(f"📚 已加载书本，等待用户选择: {', '.join(loaded_books)}")
        else:
            print("⚠️ 没有加载到任何书本，请手动添加书本")
        
        # 使用这个实例创建 LangChain Agent
        from langchain_agent import create_graphrag_agent
        graph_agent = create_graphrag_agent(graph_agent_instance)
        graph_agent_instance = graph_agent_instance  # 保存引用
        
        print("✅ 代理初始化成功")
        return True
    except Exception as e:
        print(f"❌ 代理初始化失败: {e}")
        return False

@app.route('/')
def index():
    """主页"""
    return send_from_directory('frontend', 'index.html')

@app.route('/test')
def test_page():
    """测试页面"""
    return send_from_directory('frontend', 'test.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """提供静态文件"""
    return send_from_directory('frontend', filename)

@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天API - 支持流式响应"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        current_book = data.get('currentBook')
        history = data.get('history', [])
        stream = data.get('stream', False)  # 是否启用流式响应
        
        if not graph_agent:
            return jsonify({'error': '代理未初始化'}), 500
        
        # 构建历史对话
        chat_history = []
        for msg in history[-10:]:  # 只保留最近10条消息
            if msg['type'] == 'user':
                chat_history.append(f"用户: {msg['content']}")
            elif msg['type'] == 'assistant':
                chat_history.append(f"助手: {msg['content']}")
        
        if stream:
            # 流式响应（SSE）
            def generate():
                try:
                    # 初始状态
                    yield "event: status\n"
                    yield f"data: {json.dumps({'prompt':'正在分析问题...'}, ensure_ascii=False)}\n\n"

                    # 创建新的队列实例，确保完全清空
                    callback_queue = queue.Queue()
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    def callback_yield(sse_chunk: str):
                        # 这里 sse_chunk 已经是 "event:...\n data:...\n\n" 的完整片段
                        callback_queue.put(sse_chunk)

                    # 为每个请求创建新的回调处理器实例
                    callback_handler = StreamingCallbackHandler(callback_yield)
                    print(f"🆕 创建新的回调处理器: {callback_handler._run_id}")

                    def run_agent():
                        try:
                            print(f"🤖 开始执行代理: {message}")
                            resp = loop.run_until_complete(
                                graph_agent.ainvoke(
                                    {"input": message, "chat_history": chat_history},
                                    config={"callbacks": [callback_handler]}
                                )
                            )
                            print(f"✅ 代理执行完成: {type(resp)}")
                            callback_queue.put(("response", resp))
                        except Exception as e:
                            print(f"❌ 代理执行失败: {e}")
                            callback_queue.put(("error", str(e)))

                    agent_thread = threading.Thread(target=run_agent, daemon=True)
                    agent_thread.start()

                    response = None
                    message_count = 0
                    while True:
                        try:
                            item = callback_queue.get(timeout=0.1)
                            message_count += 1
                            print(f"📨 收到队列消息 #{message_count}: {type(item)}")
                            
                            if isinstance(item, tuple):
                                if item[0] == "response":
                                    print(f"🎯 收到最终响应")
                                    response = item[1]
                                    break
                                elif item[0] == "error":
                                    print(f"💥 收到错误: {item[1]}")
                                    raise Exception(item[1])
                            else:
                                # 由回调器构造的 SSE 事件，直接透传
                                print(f"📡 转发SSE消息: {item[:100]}...")
                                yield item
                        except queue.Empty:
                            if not agent_thread.is_alive():
                                print(f"🔚 代理线程已结束，退出循环")
                                break
                            continue

                    agent_thread.join()

                    # 结束发送 final/done
                    if isinstance(response, dict) and 'output' in response:
                        output = response['output']
                    else:
                        output = str(response)

                    # 尝试规约中间步骤（工具名 + 参数/观测摘要）
                    intermediate = []
                    if isinstance(response, dict):
                        for st in response.get("intermediate_steps", []):
                            try:
                                action, observation = st
                                intermediate.append({
                                    "tool": getattr(action, "tool", "unknown"),
                                    "argsPreview": str(getattr(action, "tool_input", ""))[:300],
                                    "observationPreview": str(observation)[:500]
                                })
                            except Exception:
                                pass

                    final_payload = {
                        'response': output,
                        'currentBook': graph_agent_instance.get_current_book() if hasattr(graph_agent_instance, 'get_current_book') else current_book,
                        'needBookSelection': ("需要选择书本" in output) or ("请先选择" in output),
                        'intermediate': intermediate
                    }
                    yield "event: final\n"
                    yield f"data: {json.dumps(final_payload, ensure_ascii=False)}\n\n"
                    yield "event: done\n"
                    yield "data: {}\n\n"

                except Exception as e:
                    yield "event: error\n"
                    yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

            return app.response_class(
                generate(),
                mimetype='text/event-stream',  # <<< 关键
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no'  # Nginx 下关闭缓冲
                }
            )
        else:
            # 非流式响应（保持原有逻辑）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                response = loop.run_until_complete(graph_agent.ainvoke({
                    "input": message,
                    "chat_history": chat_history
                }))
                steps = []
                if isinstance(response, dict):
                    for st in response.get("intermediate_steps", []):
                        try:
                            action, observation = st
                            steps.append({
                                "tool": getattr(action, "tool", "unknown"),
                                "argsPreview": str(getattr(action, "tool_input", ""))[:300],
                                "observationPreview": str(observation)[:500]
                            })
                        except Exception:
                            pass
                # 解析响应
                if isinstance(response, dict) and 'output' in response:
                    output = response['output']
                else:
                    output = str(response)
                
                # 检查是否需要选择书本
                if "需要选择书本" in output or "请先选择" in output:
                    return jsonify({
                        'response': output,
                        'needBookSelection': True,
                        'currentBook': current_book
                    })
                
                return jsonify({
                    'response': output,
                    'currentBook': graph_agent_instance.get_current_book() if hasattr(graph_agent_instance, 'get_current_book') else current_book,
                    'toolCalls': []
                })
                
            finally:
                loop.close()
            
    except Exception as e:
        print(f"聊天API错误: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/books', methods=['GET'])
def list_books():
    """获取书本列表"""
    try:
        if not graph_agent_instance:
            return jsonify({'error': '代理未初始化'}), 500
        
        book_names = graph_agent_instance.list_books() if hasattr(graph_agent_instance, 'list_books') else []
        current_book = graph_agent_instance.get_current_book() if hasattr(graph_agent_instance, 'get_current_book') else None
        
        # 返回更详细的书本信息
        books = []
        for name in book_names:
            books.append({
                'name': name,
                'isCurrent': name == current_book
            })
        
        print(f"📚 返回书本列表: {books}")
        return jsonify(books)
        
    except Exception as e:
        print(f"获取书本列表错误: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/switch-book', methods=['POST'])
def switch_book():
    """切换书本"""
    try:
        data = request.get_json()
        book_name = data.get('bookName')
        
        if not graph_agent_instance:
            return jsonify({'error': '代理未初始化'}), 500
        
        if hasattr(graph_agent_instance, 'switch_book'):
            graph_agent_instance.switch_book(book_name)
            return jsonify({'success': True, 'currentBook': book_name})
        else:
            return jsonify({'error': '切换书本功能不可用'}), 500
            
    except Exception as e:
        print(f"切换书本错误: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/add-book', methods=['POST'])
def add_book():
    """添加书本"""
    try:
        data = request.get_json()
        path = data.get('path')
        name = data.get('name')
        
        if not graph_agent_instance:
            return jsonify({'error': '代理未初始化'}), 500
        
        if hasattr(graph_agent_instance, 'add_book'):
            graph_agent_instance.add_book(name, path)
            return jsonify({'success': True})
        else:
            return jsonify({'error': '添加书本功能不可用'}), 500
            
    except Exception as e:
        print(f"添加书本错误: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/current-book', methods=['GET'])
def get_current_book():
    """获取当前书本"""
    try:
        if not graph_agent_instance:
            return jsonify({'error': '代理未初始化'}), 500
        
        current_book = graph_agent_instance.get_current_book() if hasattr(graph_agent_instance, 'get_current_book') else None
        return jsonify({'currentBook': current_book})
        
    except Exception as e:
        print(f"获取当前书本错误: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'agent_initialized': graph_agent is not None
    })

if __name__ == '__main__':
    print("🚀 启动智能创作助手...")
    
    # 初始化代理
    if initialize_agent():
        print("🌐 启动Web服务器...")
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("❌ 无法启动服务器，代理初始化失败")