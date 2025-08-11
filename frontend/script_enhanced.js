// 增强版本 JavaScript - 包含所有功能但优化性能
console.log('🔍 增强版本加载中...');

// 全局变量
let currentBook = null;
let chatHistory = [];
let isProcessing = false;
let elements = {};
let currentAbortController = null;

// 聊天记录持久化
function saveChatHistory() {
    try {
        localStorage.setItem('frankenstein_chat_history', JSON.stringify(chatHistory));
        console.log('💾 聊天记录已保存');
    } catch (error) {
        console.error('❌ 保存聊天记录失败:', error);
    }
}

function loadChatHistory() {
    try {
        const savedHistory = localStorage.getItem('frankenstein_chat_history');
        if (savedHistory) {
            const savedMessages = JSON.parse(savedHistory);
            console.log('📂 已加载聊天记录:', savedMessages.length, '条消息');
            
            if (elements.chatMessages) {
                elements.chatMessages.innerHTML = '';
            }
            chatHistory = [];
            
            savedMessages.forEach(msg => {
                renderMessage(msg.type, msg.content, msg.toolCalls, msg.id);
                chatHistory.push(msg);
            });
        }
    } catch (error) {
        console.error('❌ 加载聊天记录失败:', error);
    }
}

function clearChatHistory() {
    if (confirm('确定要清空所有聊天记录吗？此操作不可撤销。')) {
        chatHistory = [];
        if (elements.chatMessages) {
            elements.chatMessages.innerHTML = '';
        }
        localStorage.removeItem('frankenstein_chat_history');
        console.log('🗑️ 聊天记录已清空');
    }
}

function updateChatHistoryMessage(messageId, content) {
    const messageIndex = chatHistory.findIndex(msg => msg.id === messageId);
    if (messageIndex !== -1) {
        chatHistory[messageIndex].content = content;
        saveChatHistory();
        console.log('💾 已更新聊天记录中的消息:', messageId);
    }
}

// 渲染消息（不保存到历史记录）
function renderMessage(type, content, toolCalls = null, messageId = null) {
    if (!elements.chatMessages) return null;
    
    console.log('🎨 渲染消息:', type, messageId);
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    if (messageId) {
        messageDiv.id = messageId;
    }
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const textDiv = document.createElement('div');
    textDiv.className = 'message-text';
    
    // 设置头像
    switch(type) {
        case 'user':
            avatar.innerHTML = '<i class="fas fa-user"></i>';
            break;
        case 'assistant':
            avatar.innerHTML = '<i class="fas fa-robot"></i>';
            break;
        case 'system':
            avatar.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
            break;
        default:
            avatar.innerHTML = '<i class="fas fa-message"></i>';
    }
    
    // 格式化内容
    textDiv.innerHTML = formatMessage(content);
    
    contentDiv.appendChild(avatar);
    contentDiv.appendChild(textDiv);
    messageDiv.appendChild(contentDiv);
    
    elements.chatMessages.appendChild(messageDiv);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    
    return messageDiv;
}

// 格式化消息内容
function formatMessage(content) {
    if (!content) return '';
    
    return content
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>');
}

// 添加消息到历史记录和界面
function addMessage(type, content, toolCalls = null, messageId = null) {
    const messageElement = renderMessage(type, content, toolCalls, messageId);
    
    const message = {
        type: type,
        content: content,
        timestamp: new Date().toISOString(),
        id: messageId || 'msg-' + Date.now(),
        toolCalls: toolCalls
    };
    
    if (!chatHistory.find(msg => msg.id === message.id)) {
        chatHistory.push(message);
        saveChatHistory();
    }
    
    return messageElement;
}

// 优化的打字机效果 - 防止无限循环
function typewriterEffect(element, text, speed = 20) {
    return new Promise((resolve) => {
        if (!element || typeof text !== 'string' || text.length === 0) {
            console.warn('⚠️ 打字机效果参数无效，直接显示文本');
            if (element) element.innerHTML = text || '';
            resolve();
            return;
        }
        
        let displayText = '';
        let index = 0;
        let isRunning = true;
        
        // 安全机制：最大执行时间限制
        const maxDuration = 30000; // 30秒
        const startTime = Date.now();
        
        function typeChar() {
            // 安全检查：防止无限循环
            if (!isRunning || Date.now() - startTime > maxDuration) {
                console.warn('⚠️ 打字机效果超时或被停止，直接显示剩余文本');
                element.innerHTML = text;
                resolve();
                return;
            }
            
            try {
                if (index < text.length) {
                    let charToAdd = '';
                    
                    // 处理HTML标签
                    if (text[index] === '<') {
                        const tagEnd = text.indexOf('>', index);
                        if (tagEnd !== -1) {
                            charToAdd = text.substring(index, tagEnd + 1);
                            index = tagEnd + 1;
                        } else {
                            charToAdd = text[index];
                            index++;
                        }
                    } else {
                        charToAdd = text[index];
                        index++;
                    }
                    
                    displayText += charToAdd;
                    element.innerHTML = displayText + '<span class="typing-cursor">|</span>';
                    
                    // 滚动到底部
                    if (elements.chatMessages) {
                        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
                    }
                    
                    setTimeout(typeChar, speed);
                } else {
                    // 完成，移除光标
                    element.innerHTML = displayText;
                    resolve();
                }
            } catch (error) {
                console.error('❌ 打字机效果出错:', error);
                element.innerHTML = text;
                resolve();
            }
        }
        
        typeChar();
        
        // 提供停止机制
        element._stopTypewriter = () => {
            isRunning = false;
        };
    });
}

// 键盘事件处理
function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// 自动调整文本区域高度
function autoResizeTextarea() {
    if (elements.messageInput) {
        elements.messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });
    }
}

// 发送消息
async function sendMessage() {
    const message = elements.messageInput?.value?.trim();
    if (!message || isProcessing) return;
    
    console.log('📤 发送消息:', message);
    
    // 添加用户消息
    const userMessageId = 'user-' + Date.now();
    addMessage('user', message, null, userMessageId);
    elements.messageInput.value = '';
    if (elements.messageInput) {
        elements.messageInput.style.height = 'auto';
    }
    
    // 显示加载状态
    showLoading(true);
    isProcessing = true;
    toggleStopButton(true);
    
    // 创建新的AbortController
    currentAbortController = new AbortController();
    
            // 清空并显示思考过程
        clearThinkingProcess();
        showThinkingProcess();
        
        // 添加初始思考步骤
        addThinkingStep('info', '🎯 理解问题', `正在分析问题: "${message}"`);
        addThinkingStep('plan', '📋 制定策略', '正在制定回答策略，准备调用相关工具...');
    
    try {
        // 创建助手消息容器
        const assistantMessageId = 'msg-' + Date.now();
        const assistantMessage = renderMessage('assistant', '正在思考...', null, assistantMessageId);
        
        // 添加到聊天记录中，但内容为空，等待后续更新
        chatHistory.push({
            type: 'assistant',
            content: '',
            timestamp: new Date().toISOString(),
            id: assistantMessageId,
            toolCalls: null
        });
        
        console.log('📝 创建助手消息，ID:', assistantMessageId);
        
        // 发送到后端（启用流式响应）
        console.log('🚀 开始发送请求到后端');
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                currentBook: currentBook,
                history: chatHistory.slice(-10),
                stream: true  // 启用流式响应
            }),
            signal: currentAbortController.signal
        });
        
        console.log('📡 收到后端响应，状态:', response.status);
        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ 请求失败，状态:', response.status, '错误信息:', errorText);
            throw new Error(`网络请求失败: ${response.status} - ${errorText}`);
        }
        
        // 处理流式响应
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finalResponse = null;
        let currentEvent = null;  // 移到这里，在整个流处理过程中保持状态
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                console.log('📡 SSE流已结束');
                break;
            }
            
            const chunk = decoder.decode(value, { stream: true });
            buffer += chunk;
            console.log('📡 收到SSE数据块:', chunk.length, '字符');
            
            const lines = buffer.split('\n');
            buffer = lines.pop();
            
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i];
                
                if (line.startsWith('event: ')) {
                    currentEvent = line.slice(7);
                    console.log('📡 收到事件类型:', currentEvent);
                } else if (line.startsWith('data: ') && currentEvent) {
                    const data = line.slice(6);
                    console.log('📊 处理数据行，事件类型:', currentEvent, '数据长度:', data.length);
                    
                    if (currentEvent === 'done') {
                        console.log('🏁 收到done事件，准备结束流');
                        break;
                    }
                    
                    try {
                        if (!data.trim()) {
                            console.log('⚠️ 收到空数据，跳过');
                            continue;
                        }
                        
                        const parsed = JSON.parse(data);
                        console.log('收到SSE事件:', currentEvent, parsed);
                        
                        // 根据事件类型处理
                        if (currentEvent === 'final') {
                            console.log('🎯 前端收到final事件:', parsed);
                            finalResponse = parsed;
                            updateAssistantMessage(assistantMessageId, { type: 'final', ...parsed }, finalResponse);
                        } else if (currentEvent === 'error') {
                            console.log('❌ 前端收到error事件:', parsed);
                            addThinkingStep('error', '发生错误', parsed.error);
                            updateAssistantMessage(assistantMessageId, { type: 'error', error: parsed.error }, finalResponse);
                        } else {
                            // 处理其他事件类型
                            handleSSEEvent(currentEvent, parsed, assistantMessageId);
                        }
                        
                        // 不要立即重置currentEvent，让它在下一个event行或空行时重置
                    } catch (e) {
                        console.error('❌ 解析SSE数据失败:', e);
                        console.error('❌ 事件类型:', currentEvent);
                        console.error('❌ 原始数据:', data);
                        if (currentEvent === 'final') {
                            updateAssistantMessage(assistantMessageId, { type: 'error', error: 'JSON解析失败: ' + e.message }, null);
                        }
                    }
                } else if (line === '') {
                    currentEvent = null;
                }
            }
        }
        
        // 更新书本状态
        if (finalResponse && finalResponse.currentBook) {
            updateCurrentBook(finalResponse.currentBook);
        }
        
    } catch (error) {
        console.error('❌ 发送消息失败:', error);
        
        // 检查是否是用户主动取消
        if (error.name === 'AbortError') {
            console.log('🛑 请求被用户取消');
            // 不显示错误消息，因为stopGeneration函数已经显示了停止消息
        } else {
            addMessage('system', '抱歉，发送消息时出现错误。请稍后重试。');
            addThinkingStep('error', '请求失败', error.message);
        }
    } finally {
        showLoading(false);
        isProcessing = false;
        toggleStopButton(false);
        currentAbortController = null;
    }
}

// 工具名称到人性化描述的映射
const toolDescriptions = {
    'global_search_retrieve_tool': {
        start: '🔍 正在从知识图谱中搜索相关信息...',
        end: '✅ 已获取到相关的背景知识和上下文信息',
        thinking: '让我先搜索一下相关的信息'
    },
    'local_search_retrieve_tool': {
        start: '📚 正在本地文档中查找相关内容...',
        end: '✅ 已找到相关的文档片段',
        thinking: '让我查找一下本地文档中的相关信息'
    },
    'community_search_tool': {
        start: '👥 正在社区数据中搜索相关讨论...',
        end: '✅ 已获取到社区相关讨论内容',
        thinking: '让我看看社区中有什么相关的讨论'
    }
};

// 处理SSE事件
function handleSSEEvent(eventType, data, assistantMessageId) {
    console.log('处理SSE事件:', eventType, data);
    
    switch (eventType) {
        case 'thinking':
            if (data.content) {
                addThinkingStep('thinking', '🧠 深度思考', data.content);
            }
            break;
            
        case 'tool_start':
            if (data.tool && data.tool.includes('global_search_retrieve')) {
                addThinkingStep('tool', '🔍 知识图谱检索', '正在从知识图谱中搜索相关信息...');
            } else if (data.tool && data.tool.includes('local_search_retrieve')) {
                addThinkingStep('tool', '📚 本地文档检索', '正在本地文档中查找相关内容...');
            } else if (data.tool && data.tool.includes('community_search')) {
                addThinkingStep('tool', '👥 社区数据搜索', '正在社区数据中搜索相关讨论...');
            } else if (data.tool && data.tool.includes('global_search_generate')) {
                addThinkingStep('tool', '🎯 智能生成', '正在基于检索到的信息生成回答...');
            } else if (data.toolName || data.tool) {
                const toolName = data.toolName || data.tool;
                const desc = toolDescriptions[toolName];
                if (desc) {
                    addThinkingStep('tool', desc.start.split(' ')[0], desc.start);
                } else {
                    addThinkingStep('tool', '🔧 工具执行', `正在使用工具: ${toolName}`);
                }
            }
            break;
            
        case 'tool_end':
            if (data.tool && data.tool.includes('global_search_retrieve')) {
                addThinkingStep('success', '✅ 检索完成', '已从知识图谱中获取到相关的背景知识和上下文信息');
            } else if (data.tool && data.tool.includes('local_search_retrieve')) {
                addThinkingStep('success', '✅ 检索完成', '已从本地文档中找到相关的文档片段');
            } else if (data.tool && data.tool.includes('community_search')) {
                addThinkingStep('success', '✅ 搜索完成', '已获取到社区相关讨论内容');
            } else if (data.tool && data.tool.includes('global_search_generate')) {
                addThinkingStep('success', '✅ 生成完成', '已基于检索信息完成智能回答生成');
            } else if (data.toolName || data.tool) {
                const toolName = data.toolName || data.tool;
                const desc = toolDescriptions[toolName];
                if (desc) {
                    addThinkingStep('success', '✅ 完成', desc.end);
                } else {
                    addThinkingStep('success', '✅ 完成', `工具 ${toolName} 执行完成`);
                }
            }
            break;
            
        case 'llm_start':
            if (data.model) {
                addThinkingStep('thinking', '🤖 AI推理', `正在使用 ${data.model} 进行智能推理...`);
            }
            break;
            
        case 'llm_end':
            if (data.usage && data.usage.finish_reason === 'stop') {
                addThinkingStep('success', '✅ 推理完成', 'AI推理过程已完成');
            }
            break;
            
        case 'run_start':
            addThinkingStep('info', '🚀 开始执行', '开始执行智能分析流程...');
            break;
            
        case 'run_end':
            // 不显示太多重复的run_end事件
            break;
            
        case 'plan':
            if (data.content) {
                addThinkingStep('plan', '📋 策略制定', data.content);
            } else if (data.nextTool) {
                addThinkingStep('plan', '📋 执行计划', `下一步将使用: ${data.nextTool}`);
            }
            break;
            
        case 'plan_done':
            addThinkingStep('success', '🎯 计划完成', '已制定完整的执行计划，开始具体实施');
            break;
            
        case 'status':
            if (data.message) {
                addThinkingStep('info', 'ℹ️ 状态更新', data.message);
            }
            break;
            
        default:
            // 记录但不显示未知事件
            console.log('未处理的事件类型:', eventType, data);
    }
}

// 更新助手消息的函数
function updateAssistantMessage(messageId, data, finalResponse) {
    console.log('🔧 updateAssistantMessage 被调用:', messageId, data.type);
    const messageElement = document.getElementById(messageId);
    if (!messageElement) {
        console.error('❌ 找不到消息元素:', messageId);
        return;
    }
    
    const messageText = messageElement.querySelector('.message-text');
    if (!messageText) {
        console.error('❌ 找不到消息文本元素');
        return;
    }
    
    console.log('更新助手消息:', data.type, data);
    
    switch (data.type) {
        case 'final':
            console.log('🎯 显示最终回答:', data.response);
            
            // 检查response字段是否存在
            if (!data.response) {
                console.error('❌ final事件中缺少response字段!', data);
                messageText.innerHTML = '<div class="error-message">❌ 响应数据格式错误</div>';
                return;
            }
            
            // 先显示开始输出的提示
            addThinkingStep('info', '✍️ 开始输出回答', '正在为你生成回答...');
            
            // 使用优化的打字机效果显示回答
            const formattedResponse = formatMessage(data.response);
            typewriterEffect(messageText, formattedResponse, 15).then(() => {
                console.log('✅ 打字机效果完成');
                
                // 更新聊天记录中的助手回答
                updateChatHistoryMessage(messageId, data.response);
                
                // 添加最终完成的思考步骤
                addThinkingStep('success', '🎉 回答完成', '已为你生成了完整的回答');
            });
            
            // 更新书本状态
            if (data.currentBook) {
                updateCurrentBook(data.currentBook);
            }
            break;
            
        case 'error':
            console.log('❌ 显示错误信息:', data.error);
            messageText.innerHTML = `<div class="error-message">❌ ${data.error}</div>`;
            updateChatHistoryMessage(messageId, `错误: ${data.error}`);
            break;
            
        default:
            console.log('未知的消息类型:', data.type);
    }
}

// 显示/隐藏加载状态
function showLoading(show) {
    if (elements.loadingIndicator) {
        elements.loadingIndicator.style.display = show ? 'flex' : 'none';
    }
}

// 切换侧边栏
function toggleSidebar() {
    if (elements.sidebar) {
        elements.sidebar.classList.toggle('show');
    }
}

// 显示模态框
function showModal(title, content) {
    if (elements.modalTitle) elements.modalTitle.textContent = title;
    if (elements.modalBody) elements.modalBody.innerHTML = content;
    if (elements.modal) elements.modal.classList.add('show');
}

// 关闭模态框
function closeModal() {
    if (elements.modal) elements.modal.classList.remove('show');
}

// 列出书本
async function listBooks() {
    try {
        console.log('📚 获取书本列表...');
        const response = await fetch('/api/books');
        const books = await response.json();
        
        console.log('📚 收到书本列表:', books);
        
        if (elements.bookList) {
            elements.bookList.innerHTML = '';
            books.forEach(book => {
                const bookItem = document.createElement('div');
                bookItem.className = 'book-item';
                
                // 检查是否是当前书本
                const isCurrentBook = book.name === currentBook || book.isCurrent;
                if (isCurrentBook) {
                    bookItem.classList.add('active');
                    console.log('📖 标记当前书本为活动状态:', book.name);
                    
                    // 同时更新顶部显示
                    if (!currentBook) {
                        updateCurrentBook(book.name);
                    }
                }
                
                // 创建按钮并绑定事件（避免字符串拼接问题）
                const bookSpan = document.createElement('span');
                bookSpan.textContent = book.name;
                
                const switchBtn = document.createElement('button');
                switchBtn.className = 'btn btn-icon';
                switchBtn.title = `切换到 ${book.name}`;
                switchBtn.innerHTML = '<i class="fas fa-arrow-right"></i>';
                switchBtn.addEventListener('click', () => {
                    console.log('🔄 点击切换按钮，书本名称:', book.name);
                    switchBook(book.name);
                });
                
                bookItem.appendChild(bookSpan);
                bookItem.appendChild(switchBtn);
                
                elements.bookList.appendChild(bookItem);
            });
            
            console.log('📚 书本列表已更新，当前书本:', currentBook);
        }
    } catch (error) {
        console.error('❌ 获取书本列表失败:', error);
    }
}

// 切换书本
async function switchBook(bookName) {
    try {
        console.log('📖 切换到书本:', bookName, '类型:', typeof bookName);
        
        // 参数验证
        if (!bookName || bookName === 'undefined' || bookName === 'null') {
            console.error('❌ 无效的书本名称:', bookName);
            addMessage('system', '❌ 无效的书本名称');
            return;
        }
        const response = await fetch('/api/switch-book', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bookName: bookName })  // 修正字段名
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('✅ 书本切换成功:', data);
            
            // 立即更新当前书本显示
            updateCurrentBook(bookName);
            
            // 在聊天框中显示切换消息
            addMessage('assistant', `✅ 已成功切换到书本: <strong>${bookName}</strong>`);
            
            // 更新书本列表中的活动状态
            document.querySelectorAll('.book-item').forEach(item => {
                item.classList.remove('active');
                if (item.querySelector('span').textContent === bookName) {
                    item.classList.add('active');
                    console.log('✅ 更新书本列表活动状态:', bookName);
                }
            });
            
            // 强制刷新当前书本显示
            if (elements.currentBookName) {
                elements.currentBookName.textContent = bookName;
                elements.currentBookName.style.color = '#1976d2'; // 蓝色高亮
                setTimeout(() => {
                    elements.currentBookName.style.color = '';
                }, 2000); // 2秒后恢复正常颜色
            }
            
        } else {
            const errorText = await response.text();
            console.error('❌ 书本切换失败:', response.status, errorText);
            addMessage('system', `❌ 切换书本失败: ${errorText}`);
        }
    } catch (error) {
        console.error('❌ 切换书本失败:', error);
        addMessage('system', `❌ 切换书本失败: ${error.message}`);
    }
}

// 更新当前书本显示
function updateCurrentBook(bookName) {
    currentBook = bookName;
    if (elements.currentBookName) {
        elements.currentBookName.textContent = bookName || '请选择书本';
        // 如果没有选择书本，使用不同的样式提示
        if (!bookName) {
            elements.currentBookName.style.color = '#ff6b6b';
            elements.currentBookName.style.fontStyle = 'italic';
        } else {
            elements.currentBookName.style.color = '';
            elements.currentBookName.style.fontStyle = '';
        }
    }
    
    // 保存到localStorage
    if (bookName) {
        localStorage.setItem('currentBook', bookName);
    } else {
        localStorage.removeItem('currentBook');
    }
}

// 显示添加书本模态框
function showAddBookModal() {
    const content = `
        <form id="addBookForm">
            <div class="form-group">
                <label for="bookName">书本名称:</label>
                <input type="text" id="bookName" name="bookName" required>
            </div>
            <div class="form-group">
                <label for="bookPath">书本路径:</label>
                <input type="text" id="bookPath" name="bookPath" placeholder="例: ./data/my_book" required>
            </div>
            <div class="form-actions">
                <button type="submit" class="btn btn-primary">添加书本</button>
                <button type="button" class="btn btn-secondary" onclick="closeModal()">取消</button>
            </div>
        </form>
    `;
    
    showModal('添加新书本', content);
    
    // 绑定表单提交事件
    document.getElementById('addBookForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const bookData = {
            name: formData.get('bookName'),
            path: formData.get('bookPath')
        };
        
        try {
            const response = await fetch('/api/add-book', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bookData)
            });
            
            if (response.ok) {
                closeModal();
                listBooks(); // 重新加载书本列表
                addMessage('assistant', `📚 书本 "${bookData.name}" 已成功添加`);
            } else {
                const error = await response.text();
                alert('添加书本失败: ' + error);
            }
        } catch (error) {
            console.error('❌ 添加书本失败:', error);
            alert('添加书本失败: ' + error.message);
        }
    });
}

// 选择工具
function selectTool(toolName) {
    // 移除其他工具的活动状态
    if (elements.toolBtns) {
        elements.toolBtns.forEach(btn => btn.classList.remove('active'));
    }
    
    // 添加当前工具的活动状态
    const activeBtn = document.querySelector(`[data-tool="${toolName}"]`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
    
    // 在输入框中添加工具提示
    if (elements.messageInput) {
        elements.messageInput.placeholder = `使用 ${toolName} 工具...`;
        elements.messageInput.focus();
    }
}

// 清空聊天
function clearChat() {
    if (confirm('确定要清空所有聊天记录吗？')) {
        if (elements.chatMessages) {
            elements.chatMessages.innerHTML = '';
        }
        chatHistory = [];
        localStorage.removeItem('chatHistory');
        
        // 重新添加欢迎消息
        addMessage('assistant', `
            <h3>🤖 欢迎使用智能创作助手！</h3>
            
            <div class="intro-section">
                <h4>✨ 系统功能介绍</h4>
                <ul class="feature-list">
                    <li><strong>📖 深度文本分析：</strong>基于GraphRAG技术，深入理解文本内容、人物关系和情节结构</li>
                    <li><strong>🔍 智能问答：</strong>针对书籍内容进行精准问答，获取角色信息、情节分析等</li>
                    <li><strong>🎭 角色探索：</strong>深入了解书中人物的性格、关系网络和发展轨迹</li>
                    <li><strong>📝 创作辅助：</strong>基于原作风格和内容进行创作建议和灵感启发</li>
                    <li><strong>🔗 关联分析：</strong>发现文本中的隐藏联系和深层含义</li>
                </ul>
            </div>

            <div class="intro-section">
                <h4>⚡ 技术特色</h4>
                <div class="tech-highlight">
                    <p>本系统采用 <strong>GraphRAG</strong> (图增强检索生成) 技术，将文本转换为知识图谱，能够：</p>
                    <ul class="tech-list">
                        <li>🧠 理解复杂的人物关系网络</li>
                        <li>🔗 发现跨章节的情节关联</li>
                        <li>📊 提供基于图结构的深度分析</li>
                        <li>🎯 实现精准的上下文理解</li>
                    </ul>
                </div>
            </div>

            <div class="intro-section">
                <h4>🚀 如何开始</h4>
                <p><strong>第一步：</strong>从下方选择一本书籍作为分析对象</p>
                <p><strong>第二步：</strong>开始提问！例如：</p>
                <ul class="example-list">
                    <li>"这本书的主要人物有哪些？"</li>
                    <li>"分析一下主人公的性格特点"</li>
                    <li>"书中的核心冲突是什么？"</li>
                    <li>"帮我总结一下主要情节"</li>
                </ul>
            </div>

            <div class="intro-section">
                <p><strong>📚 请选择一个书本开始你的智能分析之旅：</strong></p>
                <div class="quick-actions">
                    <button class="quick-action-btn" onclick="listBooks()">
                        <i class="fas fa-list"></i> 查看可用书本
                    </button>
                    <button class="quick-action-btn" onclick="showAddBookModal()">
                        <i class="fas fa-plus"></i> 添加新书本
                    </button>
                </div>
            </div>
        `);
    }
}

// 显示系统介绍
function showSystemInfo() {
    console.log('📋 显示系统介绍');
    
    const systemIntroMessage = `
        <h3>🤖 智能创作助手 - 系统介绍</h3>
        
        <div class="intro-section">
            <h4>✨ 系统功能介绍</h4>
            <ul class="feature-list">
                <li><strong>📖 深度文本分析：</strong>基于GraphRAG技术，深入理解文本内容、人物关系和情节结构</li>
                <li><strong>🔍 智能问答：</strong>针对书籍内容进行精准问答，获取角色信息、情节分析等</li>
                <li><strong>🎭 角色探索：</strong>深入了解书中人物的性格、关系网络和发展轨迹</li>
                <li><strong>📝 创作辅助：</strong>基于原作风格和内容进行创作建议和灵感启发</li>
                <li><strong>🔗 关联分析：</strong>发现文本中的隐藏联系和深层含义</li>
            </ul>
        </div>

        <div class="intro-section">
            <h4>⚡ 技术特色</h4>
            <div class="tech-highlight">
                <p>本系统采用 <strong>GraphRAG</strong> (图增强检索生成) 技术，将文本转换为知识图谱，能够：</p>
                <ul class="tech-list">
                    <li>🧠 理解复杂的人物关系网络</li>
                    <li>🔗 发现跨章节的情节关联</li>
                    <li>📊 提供基于图结构的深度分析</li>
                    <li>🎯 实现精准的上下文理解</li>
                </ul>
            </div>
        </div>

        <div class="intro-section">
            <h4>🚀 使用指南</h4>
            <p><strong>第一步：</strong>选择一本书籍作为分析对象</p>
            <p><strong>第二步：</strong>开始提问！例如：</p>
            <ul class="example-list">
                <li>"这本书的主要人物有哪些？"</li>
                <li>"分析一下主人公的性格特点"</li>
                <li>"书中的核心冲突是什么？"</li>
                <li>"帮我总结一下主要情节"</li>
                <li>"XX和XX之间的关系如何？"</li>
                <li>"这个情节有什么深层含义？"</li>
            </ul>
        </div>

        <div class="intro-section">
            <h4>💡 使用技巧</h4>
            <ul class="tips-list">
                <li><strong>🎯 具体提问：</strong>越具体的问题，越能得到精准的答案</li>
                <li><strong>🔄 多角度探索：</strong>可以从不同角度分析同一个话题</li>
                <li><strong>📚 切换书籍：</strong>随时可以切换到其他书籍进行分析</li>
                <li><strong>🛑 随时停止：</strong>可以使用停止按钮中断AI回复</li>
            </ul>
        </div>

        <div class="intro-section">
            <p><strong>📚 当前可用书籍：</strong></p>
            <div class="quick-actions">
                <button class="quick-action-btn" onclick="listBooks()">
                    <i class="fas fa-list"></i> 查看所有书籍
                </button>
                <button class="quick-action-btn" onclick="showAddBookModal()">
                    <i class="fas fa-plus"></i> 添加新书籍
                </button>
            </div>
        </div>
    `;
    
    addMessage('assistant', systemIntroMessage);
}

// 导出聊天记录
function exportChat() {
    const chatData = {
        timestamp: new Date().toISOString(),
        currentBook: currentBook,
        messages: chatHistory
    };
    
    const dataStr = JSON.stringify(chatData, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = `chat_export_${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
}

// 显示示例
function showExample(type) {
    const examples = {
        analysis: [
            '分析一下这本书的主要主题',
            '这本书中的主要人物有哪些特点？',
            '书中的情节发展有什么特色？'
        ],
        creation: [
            '基于这本书的风格，写一个短故事',
            '续写这本书的一个章节',
            '创作一首关于这本书的诗'
        ],
        exploration: [
            '这本书与其他同类作品有什么不同？',
            '书中提到的历史背景是什么？',
            '这本书对现代社会有什么启发？'
        ]
    };
    
    const typeExamples = examples[type] || [];
    const content = `
        <h3>${type === 'analysis' ? '文本分析' : type === 'creation' ? '创意写作' : '深度探索'}示例</h3>
        <div class="example-list">
            ${typeExamples.map(example => `
                <div class="example-item" onclick="useExample('${example}')">
                    <i class="fas fa-lightbulb"></i>
                    <span>${example}</span>
                </div>
            `).join('')}
        </div>
    `;
    
    showModal('使用示例', content);
}

// 使用示例
function useExample(content) {
    if (elements.messageInput) {
        elements.messageInput.value = content;
    }
    closeModal();
    if (elements.messageInput) {
        elements.messageInput.focus();
    }
}

// 思考过程相关函数
function showThinkingProcess() {
    console.log('🧠 显示思考过程区域');
    if (elements.thinkingProcess) {
        elements.thinkingProcess.style.display = 'block';
        console.log('✅ 思考过程区域已显示');
    } else {
        console.error('❌ 找不到思考过程容器元素');
    }
    if (elements.thinkingSteps) {
        elements.thinkingSteps.innerHTML = '';
        console.log('✅ 思考步骤已清空');
    } else {
        console.error('❌ 找不到思考步骤容器元素');
    }
}

function hideThinkingProcess() {
    if (elements.thinkingProcess) {
        elements.thinkingProcess.style.display = 'none';
    }
}

function clearThinkingProcess() {
    if (elements.thinkingSteps) {
        elements.thinkingSteps.innerHTML = '';
    }
}

function toggleThinkingProcess() {
    if (!elements.thinkingSteps) return;
    
    const steps = elements.thinkingSteps;
    const toggle = document.querySelector('.thinking-toggle i');
    
    if (steps.style.display === 'none') {
        steps.style.display = 'block';
        if (toggle) toggle.className = 'fas fa-chevron-up';
    } else {
        steps.style.display = 'none';
        if (toggle) toggle.className = 'fas fa-chevron-down';
    }
}

function addThinkingStep(type, title, content) {
    console.log('🧠 添加思考步骤:', type, title, content.substring(0, 50) + '...');
    
    if (!elements.thinkingSteps) {
        console.error('❌ 找不到思考步骤容器，无法添加步骤');
        return;
    }
    
    const time = new Date().toLocaleTimeString();
    const stepDiv = document.createElement('div');
    stepDiv.className = `thinking-step thinking-step-${type}`;
    
    stepDiv.innerHTML = `
        <div class="step-header">
            <span class="step-title">${title}</span>
            <span class="step-time">${time}</span>
        </div>
        <div class="step-content">${content}</div>
    `;
    
    elements.thinkingSteps.appendChild(stepDiv);
    elements.thinkingSteps.scrollTop = elements.thinkingSteps.scrollHeight;
    
    console.log('✅ 思考步骤已添加，当前总步骤数:', elements.thinkingSteps.children.length);
    
    // 确保思考过程区域是可见的
    if (elements.thinkingProcess && elements.thinkingProcess.style.display === 'none') {
        elements.thinkingProcess.style.display = 'block';
        console.log('🔄 自动显示思考过程区域');
    }
}

// 停止生成
function stopGeneration() {
    console.log('🛑 用户请求停止生成');
    
    if (currentAbortController) {
        currentAbortController.abort();
        currentAbortController = null;
    }
    
    // 重置UI状态
    showLoading(false);
    isProcessing = false;
    toggleStopButton(false);
    
    // 显示停止消息
    addMessage('assistant', '🛑 生成已停止');
    
    console.log('✅ 生成已停止');
}

// 切换停止按钮显示状态
function toggleStopButton(show) {
    if (elements.stopBtn && elements.sendBtn) {
        if (show) {
            elements.stopBtn.style.display = 'block';
            elements.sendBtn.style.display = 'none';
        } else {
            elements.stopBtn.style.display = 'none';
            elements.sendBtn.style.display = 'block';
        }
    }
}

// 事件监听器初始化
function initializeEventListeners() {
    // 发送消息
    if (elements.sendBtn) {
        elements.sendBtn.addEventListener('click', sendMessage);
    }
    if (elements.stopBtn) {
        elements.stopBtn.addEventListener('click', stopGeneration);
    }
    if (elements.messageInput) {
        elements.messageInput.addEventListener('keydown', handleKeyDown);
    }
    
    // 侧边栏切换
    if (elements.sidebarToggle) {
        elements.sidebarToggle.addEventListener('click', toggleSidebar);
    }
    
    // 模态框关闭
    const modalClose = document.querySelector('.modal-close');
    if (modalClose) {
        modalClose.addEventListener('click', closeModal);
    }
    if (elements.modal) {
        elements.modal.addEventListener('click', function(e) {
            if (e.target === elements.modal) closeModal();
        });
    }
    
    // 书本管理
    if (elements.listBooksBtn) {
        elements.listBooksBtn.addEventListener('click', listBooks);
    }
    if (elements.addBookBtn) {
        elements.addBookBtn.addEventListener('click', showAddBookModal);
    }
    
    // 工具按钮
    if (elements.toolBtns) {
        elements.toolBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const tool = this.dataset.tool;
                // 如果当前按钮已经是活动状态，则取消选中
                if (this.classList.contains('active')) {
                    this.classList.remove('active');
                    // 清除输入框中的工具提示
                    if (elements.messageInput && elements.messageInput.placeholder.includes('工具')) {
                        elements.messageInput.placeholder = '输入您的问题...';
                    }
                } else {
                    selectTool(tool);
                }
            });
        });
    }
    
    // 聊天管理
    if (elements.clearChatBtn) {
        elements.clearChatBtn.addEventListener('click', clearChatHistory);
    }
    if (elements.exportChatBtn) {
        elements.exportChatBtn.addEventListener('click', exportChat);
    }
    
    // 系统介绍
    if (elements.infoBtn) {
        elements.infoBtn.addEventListener('click', showSystemInfo);
    }
    
    // 设置变化
    const autoSaveCheckbox = document.getElementById('autoSave');
    if (autoSaveCheckbox) {
        autoSaveCheckbox.addEventListener('change', function() {
            localStorage.setItem('autoSave', this.checked);
        });
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 增强版本初始化开始...');
    
    try {
        // 初始化DOM元素
        elements = {
            messageInput: document.getElementById('messageInput'),
            sendBtn: document.getElementById('sendBtn'),
            stopBtn: document.getElementById('stopBtn'),
            chatMessages: document.getElementById('chatMessages'),
            sidebarToggle: document.getElementById('sidebarToggle'),
            sidebar: document.querySelector('.sidebar'),
            modal: document.getElementById('modal'),
            modalTitle: document.getElementById('modalTitle'),
            modalBody: document.getElementById('modalBody'),
            loadingIndicator: document.getElementById('loadingIndicator'),
            listBooksBtn: document.getElementById('listBooksBtn'),
            addBookBtn: document.getElementById('addBookBtn'),
            bookList: document.getElementById('bookList'),
            currentBookName: document.getElementById('currentBookName'),
            clearChatBtn: document.getElementById('clearChatBtn'),
            exportChatBtn: document.getElementById('exportChatBtn'),
            infoBtn: document.getElementById('infoBtn'),
            toolBtns: document.querySelectorAll('.tool-btn'),
            thinkingProcess: document.getElementById('thinkingProcess'),
            thinkingSteps: document.getElementById('thinkingSteps')
        };
        
        console.log('🔍 关键元素检查:', {
            messageInput: !!elements.messageInput,
            sendBtn: !!elements.sendBtn,
            chatMessages: !!elements.chatMessages,
            thinkingProcess: !!elements.thinkingProcess
        });
        
        // 初始化事件监听器
        console.log('🎧 初始化事件监听器...');
        initializeEventListeners();
        
        // 初始化文本区域自动调整
        console.log('📝 初始化文本区域...');
        autoResizeTextarea();
        
        // 加载保存的聊天记录
        console.log('📚 加载聊天记录...');
        loadChatHistory();
        
        // 获取书本列表
        console.log('📖 获取书本列表...');
        setTimeout(() => {
            listBooks();
        }, 100);
        
        // 不自动恢复书本选择，让用户主动选择
        updateCurrentBook(null);
        console.log('📚 等待用户选择书本');
        
        // 恢复自动保存设置
        const autoSave = localStorage.getItem('autoSave');
        const autoSaveCheckbox = document.getElementById('autoSave');
        if (autoSaveCheckbox && autoSave !== null) {
            autoSaveCheckbox.checked = autoSave === 'true';
        }
        
        console.log('✅ 增强版本初始化完成');
    } catch (error) {
        console.error('❌ 初始化失败:', error);
    }
});

// 导出全局函数供HTML调用
window.listBooks = listBooks;
window.showExample = showExample;
window.switchBook = switchBook;
window.useExample = useExample;
window.toggleThinkingProcess = toggleThinkingProcess;
window.clearChatHistory = clearChatHistory;
