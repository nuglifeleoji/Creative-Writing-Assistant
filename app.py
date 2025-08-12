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
from polish_agent import create_polish_agent
from cross_book_agent import create_cross_langchain_agent
from langchain.callbacks.base import BaseCallbackHandler
from typing import Any, Dict, List
from langchain_core.agents import AgentAction, AgentFinish

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局变量
graph_agent = None
graph_agent_instance = None  # 保存 GraphAnalysisAgent 实例的引用
polish_agent = None          # 独立润色 Agent
cross_agent = None           # 跨书创作 Agent

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
        # 对于 token 事件：不去重，直接推送，实现真流式输出
        if etype == "llm_token":
            sse_message = f"event: {etype}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            self.yield_func(sse_message)
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

        # 初始化独立润色Agent
        global polish_agent
        polish_agent = create_polish_agent()
        # 初始化跨书Agent
        global cross_agent
        cross_agent = create_cross_langchain_agent()
        
        print("✅ 代理初始化成功")
        return True
    except Exception as e:
        print(f"❌ 代理初始化失败: {e}")
        return False

try:
    if os.environ.get("INIT_ON_IMPORT", "1") == "1" and graph_agent is None:
        print("⚙️ WSGI 导入阶段：尝试自动初始化 Agent...")
        initialize_agent()
except Exception as _import_init_err:
    print(f"⚠️ 导入期初始化异常（可忽略，将在首个请求时再试）：{_import_init_err}")

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
        
        # 解析当前书本（优先以后端实际选择为准）
        try:
            backend_current_book = graph_agent_instance.get_current_book() if hasattr(graph_agent_instance, 'get_current_book') else None
        except Exception:
            backend_current_book = None
        effective_current_book = backend_current_book or current_book

        # 将当前书本显式注入到Agent输入，避免“这本书”歧义
        message_for_agent = message
        if effective_current_book:
            message_for_agent = (
                f"【当前书本】{effective_current_book}\n"
                f"【任务】请基于当前书本回答下述问题；若用户提到‘这本书’，默认指当前书本。\n"
                f"【用户问题】{message}"
            )

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
                                    {"input": message_for_agent, "chat_history": chat_history},
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
                        'currentBook': effective_current_book,
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
                    "input": message_for_agent,
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
                    'currentBook': effective_current_book,
                    'toolCalls': []
                })
                
            finally:
                loop.close()
            
    except Exception as e:
        print(f"聊天API错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/polish', methods=['POST'])
def api_polish():
    """润色API：根据草稿与历史对话进行润色，支持SSE流式输出。"""
    try:
        data = request.get_json(silent=True) or {}
        draft = data.get('draft', '')
        history = data.get('history', [])  # 可为字符串或消息数组
        user_prompt = data.get('userPrompt', '')
        tone = data.get('tone', 'neutral')
        target_length = data.get('targetLength', 'original')
        stream = data.get('stream', True)

        if not draft:
            return jsonify({'error': 'draft不能为空'}), 400

        # 归一化历史为纯文本
        if isinstance(history, list):
            history_text = []
            for msg in history[-10:]:
                role = msg.get('type') or msg.get('role')
                content = msg.get('content', '')
                if role == 'user':
                    history_text.append(f"用户: {content}")
                elif role in ('assistant', 'ai'):
                    history_text.append(f"助手: {content}")
            history_text = "\n".join(history_text)
        else:
            history_text = str(history or '')

        if not stream:
            # 非流式：直接返回润色结果
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    polish_agent.polish_async(
                        draft=draft,
                        chat_history_text=history_text,
                        user_prompt=user_prompt,
                        tone=tone,
                        target_length=target_length,
                    )
                )
                return jsonify({'result': result})
            finally:
                loop.close()

        # 流式：使用SSE返回token与最终结果
        def generate():
            try:
                yield "event: status\n"
                yield f"data: {json.dumps({'status': '开始润色...'}, ensure_ascii=False)}\n\n"

                callback_q = queue.Queue()

                class PolishStreamingHandler(BaseCallbackHandler):
                    def __init__(self, yield_fn):
                        self.yield_fn = yield_fn
                    def on_llm_start(self, serialized, prompts, **kwargs):
                        self.yield_fn(f"event: llm_start\ndata: {json.dumps({'model': serialized.get('name','llm')}, ensure_ascii=False)}\n\n")
                    def on_llm_new_token(self, token: str, **kwargs):
                        # 发送token，实现真流式
                        self.yield_fn(f"event: llm_token\ndata: {json.dumps({'token': token}, ensure_ascii=False)}\n\n")
                    def on_llm_end(self, response, **kwargs):
                        # 发送一个空对象，表示该段token流结束
                        self.yield_fn("event: llm_end\n")
                        self.yield_fn("data: {}\n\n")

                def q_yield(sse_chunk: str):
                    callback_q.put(sse_chunk)

                handler = PolishStreamingHandler(q_yield)

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def run_polish():
                    from langchain_core.messages import SystemMessage, HumanMessage
                    system_rules = (
                        "你是一个中文写作润色助手，提升清晰度、结构性与一致性，不改变事实与核心含义。\n"
                        "- 修正语法/用词/标点/格式\n"
                        "- 优化逻辑与段落衔接\n"
                        "- 提升可读性与专业性，避免冗余\n"
                        "- 保留关键信息与术语，不编造内容\n"
                        f"- 目标语气: {tone}；长度策略: {target_length}"
                    )
                    hist_part = f"\n\n[对话历史]\n{history_text}" if history_text else ""
                    requirement_part = f"\n\n[用户需求（必须严格满足）]\n{user_prompt}" if user_prompt else ""
                    prompt = (
                        "请先对照[用户需求]检查草稿是否完全符合要求（题材、风格、结构、长度、禁忌等）。若存在不符合或遗漏，请在润色时一并修正；否则在保持含义不变的前提下优化表达。\n"
                        "仅输出润色后的最终文本，不要输出解释或打分。\n\n"
                        f"[草稿]\n{draft}{hist_part}{requirement_part}"
                    )
                    messages = [SystemMessage(content=system_rules), HumanMessage(content=prompt)]

                    # 直接使用独立llm（带回调）进行流式生成
                    resp = await polish_agent.llm_polish.ainvoke(messages, config={"callbacks": [handler]})
                    return resp.content if hasattr(resp, 'content') else str(resp)

                result_text = loop.run_until_complete(run_polish())

                # 转发队列中的SSE片段
                while not callback_q.empty():
                    yield callback_q.get()

                # 最终结果
                yield "event: final\n"
                yield f"data: {json.dumps({'result': result_text}, ensure_ascii=False)}\n\n"
                yield "event: done\n"
                yield "data: {}\n\n"

            except Exception as e:
                yield "event: error\n"
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

        return app.response_class(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )

    except Exception as e:
        print(f"润色API错误: {e}")
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
            # 重置Agent对话记忆并重建执行器，避免跨书本串扰
            try:
                from langchain_agent import create_graphrag_agent, memory
                memory.clear()
                global graph_agent
                graph_agent = create_graphrag_agent(graph_agent_instance)
                print(f"🔄 已重建Agent执行器并清空记忆，当前书本: {book_name}")
            except Exception as e:
                print(f"⚠️ 重建Agent或清空记忆失败: {e}")
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

@app.route('/api/cross-chat', methods=['POST'])
def cross_chat():
    """跨书创作（SSE）：不改变currentBook，按所选书本并行检索并生成。"""
    try:
        data = request.get_json(silent=True) or {}
        books = data.get('books', [])
        prompt = data.get('message', '') or data.get('prompt', '')
        history = data.get('history', [])
        mode = data.get('mode', 'both')
        topk = int(data.get('topK', 5))
        if not isinstance(books, list) or len(books) == 0:
            return jsonify({'error': '请至少选择一本书'}), 400
        if not prompt:
            return jsonify({'error': 'prompt不能为空'}), 400

        def generate():
            try:
                yield "event: status\n"
                yield f"data: {json.dumps({'status':'开始并行检索上下文...'}, ensure_ascii=False)}\n\n"

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # 通过子Agent执行原工具链，逐书发工具事件
                sse_queue = queue.Queue()
                def sse_emit(evt, payload):
                    sse_queue.put(f"event: {evt}\n" + f"data: {json.dumps(payload, ensure_ascii=False)}\n\n")

                from cross_book_agent import CrossOrchestrator
                orchestrator = CrossOrchestrator(sse_emit)

                # 回调handler工厂：重用现有 StreamingCallbackHandler 以推送 llm/tool 事件
                def handler_factory_for_book(book_label: str):
                    def yield_with_book(s: str):
                        try:
                            if s.startswith("event:"):
                                # inject book into data json
                                parts = s.split("\n")
                                if len(parts) >= 2 and parts[1].startswith("data: "):
                                    et = parts[0][7:].strip()
                                    raw = parts[1][6:]
                                    payload = json.loads(raw)
                                    if isinstance(payload, dict):
                                        payload['book'] = book_label
                                        s_mod = f"event: {et}\n" + f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                                        sse_queue.put(s_mod)
                                        return
                        except Exception:
                            pass
                        sse_queue.put(s)
                    return StreamingCallbackHandler(yield_with_book)

                # 为每本书创建带book标记的回调handler
                def cb_factory_picker(book_name: str):
                    return lambda: handler_factory_for_book(book_name)

                # 运行并发子代理（实时推送事件）
                contexts_holder = {"data": None, "error": None}

                async def run_all():
                    from cross_book_agent import CrossOrchestrator
                    orch = orchestrator
                    tasks = []
                    for b in books:
                        tasks.append(orch._run_one_book_agent(b, prompt, history or [], cb_factory_picker(b)))
                    return await asyncio.gather(*tasks)

                def run_retrieve_thread():
                    try:
                        contexts_holder["data"] = loop.run_until_complete(run_all())
                    except Exception as re:
                        contexts_holder["error"] = str(re)

                retrieve_thread = threading.Thread(target=run_retrieve_thread, daemon=True)
                retrieve_thread.start()

                # 实时转发回调输出（检索阶段）
                while True:
                    try:
                        chunk = sse_queue.get(timeout=0.1)
                        yield chunk
                    except queue.Empty:
                        if not retrieve_thread.is_alive():
                            break
                        continue

                retrieve_thread.join()

                if contexts_holder["error"]:
                    yield "event: error\n"
                    yield f"data: {json.dumps({'error': contexts_holder['error']}, ensure_ascii=False)}\n\n"
                    return
                contexts = contexts_holder["data"] or []

                # 构造生成消息（融合）
                messages = cross_agent.build_messages(contexts, prompt)

                # 流式生成
                class CrossStreamHandler(BaseCallbackHandler):
                    def __init__(self, yield_fn):
                        self.yield_fn = yield_fn
                    def on_llm_start(self, serialized, prompts, **kwargs):
                        self.yield_fn(f"event: llm_start\ndata: {json.dumps({'model': serialized.get('name','llm')}, ensure_ascii=False)}\n\n")
                    def on_llm_new_token(self, token: str, **kwargs):
                        self.yield_fn(f"event: llm_token\ndata: {json.dumps({'token': token}, ensure_ascii=False)}\n\n")
                    def on_llm_end(self, response, **kwargs):
                        self.yield_fn("event: llm_end\n")
                        self.yield_fn("data: {}\n\n")

                handler = CrossStreamHandler(lambda s: None)

                async def run_gen():
                    resp = await cross_agent.llm_gen.ainvoke(messages, config={"callbacks": [handler]})
                    return resp.content if hasattr(resp, 'content') else str(resp)

                # 通过回调直接yieldsse：重写yield函数（实时推送到队列）
                output_queue = queue.Queue()
                def sse_yield(s):
                    output_queue.put(s)

                # 替换handler的yield_fn
                handler.yield_fn = sse_yield

                final_holder = {"text": None, "error": None}

                # 在后台线程执行生成，主线程持续从队列取事件并向前端推送
                def run_gen_thread():
                    try:
                        result = loop.run_until_complete(run_gen())
                        final_holder["text"] = result
                    except Exception as ge:
                        final_holder["error"] = str(ge)

                gen_thread = threading.Thread(target=run_gen_thread, daemon=True)
                gen_thread.start()

                # 实时转发回调输出
                while True:
                    try:
                        chunk = output_queue.get(timeout=0.1)
                        yield chunk
                    except queue.Empty:
                        if not gen_thread.is_alive():
                            break
                        continue

                gen_thread.join()

                # 收尾
                if final_holder["error"]:
                    yield "event: error\n"
                    yield f"data: {json.dumps({'error': final_holder['error']}, ensure_ascii=False)}\n\n"
                else:
                    yield "event: final\n"
                    yield f"data: {json.dumps({'response': final_holder['text'] or ''}, ensure_ascii=False)}\n\n"
                yield "event: done\n"
                yield "data: {}\n\n"
            except Exception as e:
                yield "event: error\n"
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

        return app.response_class(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
    except Exception as e:
        print(f"跨书创作API错误: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/critique', methods=['POST'])
def api_critique():
    """点评API：根据文本与用户需求给出修改意见（SSE流式）。"""
    try:
        data = request.get_json(silent=True) or {}
        text = data.get('text', '')
        history = data.get('history', [])
        user_prompt = data.get('userPrompt', '')
        stream = data.get('stream', True)

        if not text:
            return jsonify({'error': 'text不能为空'}), 400

        # 历史归一化
        if isinstance(history, list):
            history_text = []
            for msg in history[-10:]:
                role = msg.get('type') or msg.get('role')
                content = msg.get('content', '')
                if role == 'user':
                    history_text.append(f"用户: {content}")
                elif role in ('assistant', 'ai'):
                    history_text.append(f"助手: {content}")
            history_text = "\n".join(history_text)
        else:
            history_text = str(history or '')

        if not stream:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    polish_agent.critique_async(
                        text=text,
                        chat_history_text=history_text,
                        criteria=f"严格对照用户需求：{user_prompt}，指出不符合点并给出简洁修改建议",
                    )
                )
                return jsonify({'critique': result})
            finally:
                loop.close()

        def generate():
            try:
                yield "event: status\n"
                yield f"data: {json.dumps({'status': '开始生成修改意见...'}, ensure_ascii=False)}\n\n"

                callback_q = queue.Queue()
                class CritiqueStreamingHandler(BaseCallbackHandler):
                    def __init__(self, yield_fn):
                        self.yield_fn = yield_fn
                    def on_llm_new_token(self, token: str, **kwargs):
                        self.yield_fn(f"event: llm_token\ndata: {json.dumps({'token': token}, ensure_ascii=False)}\n\n")

                def q_yield(sse_chunk: str):
                    callback_q.put(sse_chunk)

                handler = CritiqueStreamingHandler(q_yield)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def run_critique():
                    from langchain_core.messages import SystemMessage, HumanMessage
                    system_rules = (
                        "你是一个严谨的中文文本点评助手。\n"
                        "- 从清晰度、结构性、语气一致性、事实保真、与用户需求一致性等维度评估\n"
                        "- 指出具体可改进之处，并给出简短修改建议\n"
                        "- 不编造内容，不加入无根据的信息"
                    )
                    hist_part = f"\n\n[对话历史]\n{history_text}" if history_text else ""
                    requirement = f"\n\n[用户需求（必须严格满足）]\n{user_prompt}" if user_prompt else ""
                    prompt = (
                        "请严格对照[用户需求]点评下述文本，列出不符合点与改进建议要点；若完全符合，也请简述优化空间。\n"
                        "仅输出点评内容，不要复述原文。\n\n"
                        f"[文本]\n{text}{hist_part}{requirement}"
                    )
                    messages = [SystemMessage(content=system_rules), HumanMessage(content=prompt)]
                    resp = await polish_agent.llm_polish.ainvoke(messages, config={"callbacks": [handler]})
                    return resp.content if hasattr(resp, 'content') else str(resp)

                critique_text = loop.run_until_complete(run_critique())
                while not callback_q.empty():
                    yield callback_q.get()
                yield "event: final\n"
                yield f"data: {json.dumps({'critique': critique_text}, ensure_ascii=False)}\n\n"
                yield "event: done\n"
                yield "data: {}\n\n"
            except Exception as e:
                yield "event: error\n"
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

        return app.response_class(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
    except Exception as e:
        print(f"点评API错误: {e}")
        return jsonify({'error': str(e)}), 500
if __name__ == '__main__':
    print("🚀 启动智能创作助手...")
    
    # 初始化代理
    if initialize_agent():
        print("🌐 启动Web服务器...")
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("❌ 无法启动服务器，代理初始化失败")