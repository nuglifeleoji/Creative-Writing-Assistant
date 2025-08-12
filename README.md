# 智能创作助手（GraphRAG · 真流式 · 单书/跨书）

一个面向长文本书籍的“智能创作助手”Web 应用。后端基于 Flask + LangChain + GraphRAG，前端原生 HTML/CSS/JS（支持 SSE 真流式）。

- 支持单书与跨书创作（多书并行检索、融合生成）
- 可视化 AI 思考过程（工具调用、LLM 推理、按书分组）
- 消息内就地“润色 / 点评”按钮（真流式渲染）
- 生产可用的 SSE 流式输出（token 级）

---

## 功能特性

- 单书模式：对当前选中的书本进行 GraphRAG 检索与生成
- 跨书模式：多书并行检索，融合上下文后统一生成
- 真流式响应：后端 SSE 推送 `llm_token`，前端消息气泡实时更新
- 思考过程展示：按事件流显示 `tool_start/tool_end/llm_start/llm_token` 等
- 就地润色/点评：每条助手消息下方有图标按钮，点击即时触发 SSE 流式润色/点评
- 书本管理：列出/切换/添加书本，顶部状态显示当前选择（跨书模式显示多选结果）

---

## 代码结构

```
frontend/
  index.html            # 页面结构
  styles.css            # 样式（聊天区、思考过程、按钮、动画等）
  script_enhanced.js    # 前端逻辑：SSE 解析、UI 事件、跨书模式、润色/点评

app.py                  # Flask 入口与 API 路由（SSE、跨书编排、健康检查等）
langchain_agent.py      # 主体 LangChain Agent（工具链、检索/生成策略、streaming 回调）
cross_book_agent.py     # 跨书编排（并行运行子代理、融合上下文生成）
polish_agent.py         # 独立润色/点评 Agent（仅 LLM，开启 streaming）
prompt_utils.py         # Agent 指南/约束/输出模板（用于工具型 Agent）

search/
  rag_engine.py         # GraphRAG 引擎封装（全局/局部检索，MultiBookManager）
  quick_engine.py       # 更保守参数的快速引擎（可替换使用）

# 若有多本书的数据，位于工程根目录下若干 `bookX/` 文件夹，每个包含 output/ parquet + lancedb
```

---

## 运行环境

- Python 3.11（强烈建议）
- Windows 10/11 或 Linux（Ubuntu 20.04+）

### 必需的环境变量

在项目根目录创建 `.env`：

```
AZURE_OPENAI_API_KEY=你的_Azure_OpenAI_API_Key
# 可选：如果使用单独的嵌入密钥
Embedding_key=你的_Embedding_API_Key
```

> 注：当前默认使用 Azure OpenAI（`gpt-4o / gpt-4.1` 等），如需切换请在 `langchain_agent.py`/`polish_agent.py`/`cross_book_agent.py` 内修改部署名与版本。

---

## 安装与启动（Windows PowerShell）

```powershell
cd C:\Users\Administrator\Desktop\Frankenstein

# 仅当前会话放开脚本执行策略（安全）
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 创建并激活 Python 3.11 的虚拟环境
py -3.11 -m venv .venv311
.\.venv311\Scripts\Activate.ps1
python --version   # 应显示 Python 3.11.x

# 安装依赖
pip install -U pip
pip install -r requirements.txt

# 启动（生产更稳定：waitress）
python -m waitress --listen=0.0.0.0:5000 app:app
```

访问：

- 前端页面：`http://<服务器IP>:5000/`
- 健康检查：`http://<服务器IP>:5000/api/health`（`{"status":"healthy","agent_initialized":true}` 表示就绪）

> 无需激活方式（可选）：
> ```powershell
> .\.venv311\Scripts\python.exe -m waitress --listen=0.0.0.0:5000 app:app
> ```

---

## 安装与启动（Ubuntu）

```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv

cd /opt/frankenstein
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

# 前台验证
python -m waitress --listen=0.0.0.0:5000 app:app
```

可选：使用 systemd 永久运行

```
# /etc/systemd/system/frankenstein.service
[Unit]
Description=Frankenstein App
After=network.target

[Service]
WorkingDirectory=/opt/frankenstein
ExecStart=/opt/frankenstein/.venv/bin/python -m waitress --listen=0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 数据准备（GraphRAG 输出）

应用会在启动时自动加载 `app.py` 中列出的书本路径（默认示例）：

```
book4/output/   # 平凡的世界
book5/output/   # 三体
book6/output/   # 三体2
book7/output/   # 嫌疑人x的献身
book8/output/   # 斗罗大陆4
cxx/output/     # 超新星纪元
rag/output/     # 沙丘
rag_book2/ragtest/output/  # 白夜行
tencent/output/ # 弗兰肯斯坦
sanguo/output/  # 三国演义
```

每个 `output/` 至少包含以下文件：

- `communities.parquet`
- `entities.parquet`
- `community_reports.parquet`
- `relationships.parquet`
- `text_units.parquet`
- `lancedb/` 目录（实体描述嵌入）

若路径不存在或缺文件，后端会在控制台打印跳过原因。

---

## 前端使用说明

- 左侧“书本管理” → 列出书本 → 单书模式点击“箭头”切换当前书本
- 右上角“模式”下拉：
  - 单书模式：使用当前书本
  - 跨书模式：显示“选书”按钮，可多选书本参与创作
- 输入问题或创作指令后回车/点击发送
- 思考过程：底部“AI思考过程”会实时显示工具/LLM 事件；跨书时按书分组展示
- 就地润色/点评：每条助手消息下方两个小圆形按钮（魔法棒/对话气泡）

---

## 后端 API（精选）

- `GET /api/health`：健康检查（`agent_initialized` 指示 Agent 是否就绪）
- `GET /api/books`：列出已加载书本（含当前书本标记）
- `POST /api/switch-book`：切换当前书本 `{bookName}`
- `POST /api/add-book`：添加书本 `{name, path}`
- `POST /api/chat`：单书聊天/创作（支持 `stream=true` SSE）
- `POST /api/cross-chat`：跨书创作（SSE）
- `POST /api/polish`：润色（SSE）
- `POST /api/critique`：点评（SSE）

SSE 事件类型：`status`、`run_start/run_end`、`plan/plan_done`、`tool_start/tool_end`、`llm_start/llm_token/llm_end`、`final`、`done`、`error`

---

## 架构与关键点

### 前端（`frontend/`）

- `script_enhanced.js`
  - SSE 解码：逐行解析 `event:`/`data:`，实时更新助手消息内容
  - 真流式：在 `llm_token` 到达时直接把 token 追加到气泡
  - 思考过程：将带 `_bookTag` 的事件按书分组显示
  - 就地操作：`polishMessageById` 与 `critiqueMessageById` 通过通用 `sseToMessage` 推流
  - UI 元素在 `DOMContentLoaded` 内初始化，避免“页面无响应”

### 后端（`app.py`）

- 自定义 `StreamingCallbackHandler`：不去重 `llm_token`，保证真流式
- `initialize_agent()`：WSGI 导入期自动初始化（waitress 模式可用）
- 跨书：`/api/cross-chat` 使用 `CrossOrchestrator` 为每本书运行子代理，注入 `book` 字段到 SSE
- 润色/点评：独立 `PolishAgent`，开启 streaming，纯 LLM

### Agent 与 GraphRAG

- `langchain_agent.py`：定义工具链与主 Agent 执行器（流式回调）
- `search/rag_engine.py`：封装 GraphRAG（Global/Local 搜索）与 `MultiBookManager`
- `search/quick_engine.py`：更保守的参数（可用于更快/更稳的场景）
- `cross_book_agent.py`：并行检索每本书的上下文，构造合成提示并生成

---

## 生产部署要点（SSE 友好）

1) 后端使用 `waitress` 启动并监听 `0.0.0.0:5000`

2) 反向代理（可选，Nginx/Caddy）需关闭缓冲，示例（Nginx 片段）：

```
location /api/ {
  proxy_pass http://127.0.0.1:5000;
  proxy_set_header Connection '';
  proxy_http_version 1.1;
  chunked_transfer_encoding off;
  proxy_buffering off;        # 关键：关闭缓冲
  proxy_cache off;
}
```

3) 放行端口与防火墙

- 云厂商安全组/Windows 防火墙开放 5000（或代理端口）

---

## 常见问题（FAQ）

- `GET /api/health` 显示 `agent_initialized:false`
  - 检查书本 `output/` 路径是否存在且包含所需 parquet 与 `lancedb/`
  - 确认 `.env` 中 `AZURE_OPENAI_API_KEY` 是否正确
  - Windows 用 waitress 启动时，务必导入期初始化：本仓库已在导入期调用 `initialize_agent()`

- 前端无法列出书本/切换失效
  - 先访问 `/api/books` 看返回；若 500，多为未初始化或缺文件
  - 切换接口是 `/api/switch-book`，字段为 `bookName`

- 浏览器连接不上/`ERR_EMPTY_RESPONSE`
  - waitress 需监听 `0.0.0.0` 而非 `127.0.0.1`
  - 检查安全组与系统防火墙

- SSE 不是“真流式”
  - 确认后端未过滤 `llm_token`
  - 代理层需 `proxy_buffering off`（Nginx）

- Python 依赖安装失败（如 `contourpy`）
  - 使用 Python 3.11（建议新建 venv）

- PowerShell 无法激活 venv（`PSSecurityException`）
  - 使用：`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

---

## 开发脚手架

- 新增书本：前端“添加书本”或调用 `/api/add-book`；也可在 `app.py` 的默认列表中补充
- 切换引擎：如需使用更快的 `quick_engine.py`，可在相关模块中替换导入
- 自定义工具链/提示：见 `langchain_agent.py` 与 `prompt_utils.py`

---

