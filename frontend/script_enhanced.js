// 多选书的弹窗
async function showCrossBookSelector() {
    try {
        const res = await fetch('/api/books');
        const books = await res.json();
        const list = Array.isArray(books) ? books.map(b => b.name) : (books.books || []);
        const content = `
            <form id="crossBooksForm" class="form">
                <div class="form-group">
                    <div class="checkbox-list">
                        ${list.map(name => `
                            <label class="checkbox-item">
                                <input type="checkbox" name="crossBook" value="${name}" ${selectedCrossBooks.includes(name) ? 'checked' : ''} />
                                <span>${name}</span>
                            </label>
                        `).join('')}
                    </div>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">确定</button>
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">取消</button>
                </div>
            </form>`;
        showModal('选择跨书创作的书目', content);
        const form = document.getElementById('crossBooksForm');
        form.addEventListener('submit', e => {
            e.preventDefault();
            const boxes = form.querySelectorAll('input[name="crossBook"]:checked');
            selectedCrossBooks = Array.from(boxes).map(b => b.value);
            closeModal();
            addMessage('system', `✅ 已选择 ${selectedCrossBooks.length} 本书用于跨书创作`);
            // 立即刷新列表高亮
            listBooks();
        });
    } catch (e) {
        addMessage('system', '❌ 获取书本列表失败：' + e.message);
    }
}
// 增强版本 JavaScript - 包含所有功能但优化性能
console.log('🔍 增强版本加载中...');

// 全局变量
let currentBook = null;
let chatHistory = [];
let isProcessing = false;
let elements = {};
let currentAbortController = null;
let composeMode = 'single';
let selectedCrossBooks = [];
let assistantStreamingBuffers = {};

// 进度条相关变量
let currentProgress = {
    percentage: 0,
    currentStep: 0,
    totalSteps: 0,
    steps: [],
    startTime: null,
    estimatedTime: null
};

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
        messageDiv.setAttribute('data-message-id', messageId);
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
    
    // 包裹文本与操作条的竖直容器，便于将操作条放在消息气泡下方
    const bodyDiv = document.createElement('div');
    bodyDiv.className = 'message-content-body';
    bodyDiv.appendChild(textDiv);

    contentDiv.appendChild(avatar);
    contentDiv.appendChild(bodyDiv);

    // 针对助手消息，增加就地操作按钮（润色/修改意见）
    if (type === 'assistant') {
        const actions = document.createElement('div');
        actions.className = 'message-actions';

        const polishBtn = document.createElement('button');
        polishBtn.className = 'icon-btn';
        polishBtn.title = '润色';
        polishBtn.innerHTML = '<i class="fas fa-wand-magic-sparkles"></i>';
        polishBtn.addEventListener('click', () => polishMessageById(messageId || messageDiv.id));

        const critiqueBtn = document.createElement('button');
        critiqueBtn.className = 'icon-btn';
        critiqueBtn.title = '修改意见';
        critiqueBtn.innerHTML = '<i class="fas fa-comment-dots"></i>';
        critiqueBtn.addEventListener('click', () => critiqueMessageById(messageId || messageDiv.id));

        actions.appendChild(polishBtn);
        actions.appendChild(critiqueBtn);
        bodyDiv.appendChild(actions);
    }
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

// 带diff高亮的消息格式化
function formatMessageWithDiff(originalText, newText) {
    if (!newText) return '';
    
    // 如果原文和新文本完全相同，直接返回格式化后的文本
    if (originalText === newText) {
        return formatMessage(newText);
    }
    
    // 简单的diff算法：按段落分割并比较
    const originalParagraphs = originalText.split(/\n+/).filter(p => p.trim().length > 0);
    const newParagraphs = newText.split(/\n+/).filter(p => p.trim().length > 0);
    
    let result = '';
    let originalIndex = 0;
    let newIndex = 0;
    
    while (newIndex < newParagraphs.length) {
        const newParagraph = newParagraphs[newIndex];
        
        // 检查是否在原文中找到相似的段落
        const similarIndex = findSimilarParagraph(newParagraph, originalParagraphs, originalIndex);
        
        if (similarIndex >= 0) {
            // 找到相似段落，比较是否有修改
            const originalParagraph = originalParagraphs[similarIndex];
            if (originalParagraph !== newParagraph) {
                // 段落被修改了，高亮显示
                result += `<div class="diff-modified">${formatMessage(newParagraph)}</div>`;
            } else {
                // 段落没有变化
                result += `<div>${formatMessage(newParagraph)}</div>`;
            }
            originalIndex = similarIndex + 1;
        } else {
            // 新段落，高亮显示为新增
            result += `<div class="diff-added">${formatMessage(newParagraph)}</div>`;
        }
        
        newIndex++;
    }
    
    return result;
}

// 将文本分割成段落
function splitIntoSentences(text) {
    // 按句号、问号、感叹号分割，保留标点
    return text.split(/([。！？\n])/).filter(s => s.trim().length > 0);
}

// 查找相似的段落（改进的相似度计算）
function findSimilarParagraph(target, paragraphs, startIndex) {
    for (let i = startIndex; i < paragraphs.length; i++) {
        const paragraph = paragraphs[i];
        const similarity = calculateParagraphSimilarity(target, paragraph);
        if (similarity > 0.4) { // 提高相似度阈值
            return i;
        }
    }
    return -1;
}

// 计算两个段落的相似度（改进的算法）
function calculateParagraphSimilarity(str1, str2) {
    // 如果长度差异太大，直接返回低相似度
    const lenDiff = Math.abs(str1.length - str2.length);
    const maxLen = Math.max(str1.length, str2.length);
    if (maxLen > 0 && lenDiff / maxLen > 0.5) {
        return 0.1;
    }
    
    // 计算字符级别的相似度
    const set1 = new Set(str1.split(''));
    const set2 = new Set(str2.split(''));
    const intersection = new Set([...set1].filter(x => set2.has(x)));
    const union = new Set([...set1, ...set2]);
    
    const charSimilarity = intersection.size / union.size;
    
    // 计算词级别的相似度（简单分词）
    const words1 = str1.split(/[\s，。！？；：""''（）【】]/).filter(w => w.length > 0);
    const words2 = str2.split(/[\s，。！？；：""''（）【】]/).filter(w => w.length > 0);
    
    const wordSet1 = new Set(words1);
    const wordSet2 = new Set(words2);
    const wordIntersection = new Set([...wordSet1].filter(w => wordSet2.has(w)));
    const wordUnion = new Set([...wordSet1, ...wordSet2]);
    
    const wordSimilarity = wordUnion.size > 0 ? wordIntersection.size / wordUnion.size : 0;
    
    // 综合相似度
    return (charSimilarity * 0.3 + wordSimilarity * 0.7);
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
        
        // 初始化进度条
        initializeProgress();
        
        // 添加初始思考步骤
        addThinkingStep('info', '🎯 理解问题', `正在分析问题: "${message}"`);
        addThinkingStep('plan', '📋 制定策略', '正在制定回答策略，准备调用相关工具...');
        
        // 更新进度
        updateProgress('理解问题', 'current');
    
    try {
        if (composeMode === 'cross') {
            await sendCrossMessage(message);
            return;
        }
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

// 跨书创作：走 /api/cross-chat
async function sendCrossMessage(promptText) {
    if (!selectedCrossBooks || selectedCrossBooks.length === 0) {
        addMessage('system', '请先选择跨书创作的书目');
        return;
    }
    // 状态
    showLoading(true);
    isProcessing = true;
    toggleStopButton(true);
    currentAbortController = new AbortController();

    // 助手气泡
    const assistantMessageId = 'msg-' + Date.now();
    renderMessage('assistant', '正在思考...', null, assistantMessageId);
    chatHistory.push({ type: 'assistant', content: '', timestamp: new Date().toISOString(), id: assistantMessageId, toolCalls: null });

    try {
        const response = await fetch('/api/cross-chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ books: selectedCrossBooks, message: promptText, history: chatHistory.slice(-10), mode: 'both', topK: 5 }),
            signal: currentAbortController.signal
        });
        if (!response.ok) {
            const text = await response.text();
            throw new Error(`跨书请求失败: ${response.status} ${text}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentEvent = null;
        let finalResponse = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            buffer += chunk;
            const lines = buffer.split('\n');
            buffer = lines.pop();
            for (const line of lines) {
                if (line.startsWith('event: ')) {
                    currentEvent = line.slice(7);
                } else if (line.startsWith('data: ') && currentEvent) {
                    const data = line.slice(6);
                    if (!data.trim()) continue;
                    if (currentEvent === 'done') break;
                    try {
                        const parsed = JSON.parse(data);
                        // 将book标签映射到思考过程：如果有book，拼接在标题上
                        if (parsed && parsed.book) {
                            parsed._bookTag = parsed.book;
                        }
                        if (currentEvent === 'final') {
                            finalResponse = parsed;
                            updateAssistantMessage(assistantMessageId, { type: 'final', ...parsed }, finalResponse);
                        } else if (currentEvent === 'error') {
                            addThinkingStep('error', '发生错误', parsed.error);
                            updateAssistantMessage(assistantMessageId, { type: 'error', error: parsed.error }, finalResponse);
                        } else {
                            // 根据book对事件标题加前缀
                            if (parsed && parsed._bookTag) {
                                const bk = parsed._bookTag;
                                if (currentEvent === 'tool_start') addThinkingStepForBook(bk, 'tool', `🔧 工具开始`, parsed.tool || parsed.toolName || '');
                                else if (currentEvent === 'tool_end') addThinkingStepForBook(bk, 'success', `✅ 工具完成`, (parsed.tool || parsed.toolName || '') + ' 完成');
                                else if (currentEvent === 'llm_start') addThinkingStepForBook(bk, 'thinking', `🤖 AI推理`, '');
                                else if (currentEvent === 'llm_end') addThinkingStepForBook(bk, 'success', `✅ 推理结束`, '');
                                else if (currentEvent === 'status') addThinkingStepForBook(bk, 'info', `ℹ️ 状态`, parsed.message || '');
                                else if (currentEvent === 'per_book_context') addThinkingStepForBook(bk, 'info', `📚 上下文`, parsed.preview || '');
                                else handleSSEEvent(currentEvent, parsed, assistantMessageId);
                            } else {
                                handleSSEEvent(currentEvent, parsed, assistantMessageId);
                            }
                        }
                    } catch {}
                } else if (line === '') {
                    currentEvent = null;
                }
            }
        }
    } catch (e) {
        addMessage('system', '❌ 跨书创作失败：' + e.message);
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
                updateProgress('检索信息', 'current');
            } else if (data.tool && data.tool.includes('local_search_retrieve')) {
                addThinkingStep('tool', '📚 本地文档检索', '正在本地文档中查找相关内容...');
                updateProgress('检索信息', 'current');
            } else if (data.tool && data.tool.includes('community_search')) {
                addThinkingStep('tool', '👥 社区数据搜索', '正在社区数据中搜索相关讨论...');
                updateProgress('检索信息', 'current');
            } else if (data.tool && data.tool.includes('global_search_generate')) {
                addThinkingStep('tool', '🎯 智能生成', '正在基于检索到的信息生成回答...');
                updateProgress('生成回答', 'current');
            } else if (data.toolName || data.tool) {
                const toolName = data.toolName || data.tool;
                const desc = toolDescriptions[toolName];
                if (desc) {
                    addThinkingStep('tool', desc.start.split(' ')[0], desc.start);
                } else {
                    addThinkingStep('tool', '🔧 工具执行', `正在使用工具: ${toolName}`);
                }
                updateProgress('检索信息', 'current');
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
                updateProgress('AI推理', 'current');
            }
            break;
            
        case 'llm_end':
            if (data.usage && data.usage.finish_reason === 'stop') {
                addThinkingStep('success', '✅ 推理完成', 'AI推理过程已完成');
            }
            break;
        case 'llm_token':
            if (data && typeof data.token === 'string') {
                if (!assistantStreamingBuffers[assistantMessageId]) {
                    assistantStreamingBuffers[assistantMessageId] = '';
                    updateProgress('生成回答', 'current');
                }
                assistantStreamingBuffers[assistantMessageId] += data.token;
                const messageElement = document.getElementById(assistantMessageId);
                const messageText = messageElement?.querySelector('.message-text');
                if (messageText) {
                    messageText.innerHTML = formatMessage(assistantStreamingBuffers[assistantMessageId]);
                    if (elements.chatMessages) elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
                }
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
            
            // 检查是否已经有流式输出的内容
            const hasStreamedContent = assistantStreamingBuffers[messageId] && assistantStreamingBuffers[messageId].length > 0;
            
            if (hasStreamedContent) {
                // 如果已经有流式输出，直接更新内容，不使用打字机效果
                console.log('🔄 检测到已有流式输出，直接显示最终结果');
                const formattedResponse = formatMessage(data.response);
                messageText.innerHTML = formattedResponse;
                
                // 更新聊天记录中的助手回答
                updateChatHistoryMessage(messageId, data.response);
                
                // 添加最终完成的思考步骤
                addThinkingStep('success', '🎉 回答完成', '已为你生成了完整的回答');
                
                // 完成进度条
                updateProgress('完成输出', 'completed');
                completeProgress();
                
                // 清理流式输出缓冲区
                delete assistantStreamingBuffers[messageId];
            } else {
                // 如果没有流式输出，使用打字机效果（兼容非流式模式）
                console.log('📝 没有流式输出，使用打字机效果');
                addThinkingStep('info', '✍️ 开始输出回答', '正在为你生成回答...');
                
                const formattedResponse = formatMessage(data.response);
                typewriterEffect(messageText, formattedResponse, 15).then(() => {
                    console.log('✅ 打字机效果完成');
                    
                    // 更新聊天记录中的助手回答
                    updateChatHistoryMessage(messageId, data.response);
                    
                    // 添加最终完成的思考步骤
                    addThinkingStep('success', '🎉 回答完成', '已为你生成了完整的回答');
                    
                    // 完成进度条
                    updateProgress('完成输出', 'completed');
                    completeProgress();
                    
                    // 清理流式输出缓冲区
                    delete assistantStreamingBuffers[messageId];
                });
            }
            
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
                
                // 检查是否是当前书本 / 或跨书多选
                const isCurrentBook = book.name === currentBook || book.isCurrent;
                if (composeMode === 'cross') {
                    if (selectedCrossBooks.includes(book.name)) {
                        bookItem.classList.add('multi-selected');
                    }
                } else if (isCurrentBook) {
                    bookItem.classList.add('active');
                    console.log('📖 标记当前书本为活动状态:', book.name);
                    if (!currentBook) updateCurrentBook(book.name);
                }
                
                // 创建按钮并绑定事件（避免字符串拼接问题）
                const bookSpan = document.createElement('span');
                bookSpan.textContent = book.name;
                
                const switchBtn = document.createElement('button');
                switchBtn.className = 'btn btn-icon';
                switchBtn.title = `切换到 ${book.name}`;
                switchBtn.innerHTML = '<i class="fas fa-arrow-right"></i>';
                switchBtn.addEventListener('click', () => {
                    if (composeMode === 'cross') {
                        const idx = selectedCrossBooks.indexOf(book.name);
                        if (idx >= 0) {
                            selectedCrossBooks.splice(idx, 1);
                            bookItem.classList.remove('multi-selected');
                        } else {
                            selectedCrossBooks.push(book.name);
                            bookItem.classList.add('multi-selected');
                        }
                        console.log('🧩 跨书选择:', selectedCrossBooks);
                    } else {
                        console.log('🔄 点击切换按钮，书本名称:', book.name);
                        switchBook(book.name);
                    }
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

// 跨书/单书模式下的当前选择显示
function updateCurrentSelectionDisplay() {
    if (!elements.currentBookName) return;
    if (composeMode === 'cross') {
        if (selectedCrossBooks.length > 0) {
            elements.currentBookName.textContent = '跨书：' + selectedCrossBooks.join(', ');
        } else {
            elements.currentBookName.textContent = '跨书：请选择书本';
        }
        elements.currentBookName.style.color = '#1976d2';
        elements.currentBookName.style.fontStyle = '';
    } else {
        // 恢复单书显示
        elements.currentBookName.textContent = currentBook || '请选择书本';
        if (!currentBook) {
            elements.currentBookName.style.color = '#ff6b6b';
            elements.currentBookName.style.fontStyle = 'italic';
        } else {
            elements.currentBookName.style.color = '';
            elements.currentBookName.style.fontStyle = '';
        }
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
        <div class="info-card">
            <div class="info-header">
                <div class="info-title-left">
                    <i class="fas fa-robot"></i>
                    <div class="info-titles">
                        <h3>智能创作助手</h3>
                        <p class="info-sub">GraphRAG 加持 · 真流式 · 单书/跨书创作</p>
                    </div>
                </div>
                <div class="info-stats">
                    <div class="stat"><span class="stat-label">模式</span><span class="stat-value">单书 / 跨书</span></div>
                    <div class="stat"><span class="stat-label">流式</span><span class="stat-value">SSE</span></div>
                    <div class="stat"><span class="stat-label">润色/点评</span><span class="stat-value">已启用</span></div>
                </div>
            </div>

            <div class="info-grid">
                <section>
                    <h4>✨ 能力概览</h4>
                    <ul class="feature-list compact">
                        <li><strong>📖 深度文本分析：</strong>理解人物关系、情节结构与主题意象</li>
                        <li><strong>🔍 精准检索生成：</strong>GraphRAG 全局/局部检索 + 上下文融合回答</li>
                        <li><strong>🎭 角色探索：</strong>人物画像、关系网、关键事件关联</li>
                        <li><strong>📝 创作辅助：</strong>基于原作风格完成续写与创作</li>
                        <li><strong>🪄 润色/点评：</strong>一键润色上一条AI输出，并严格对齐用户需求</li>
                    </ul>
                </section>

                <section>
                    <h4>⚡ 技术要点</h4>
                    <div class="tech-highlight tight">
                        <ul class="tech-list bullets">
                            <li>🧠 GraphRAG：图结构检索、跨章节关联与证据聚合</li>
                            <li>🔗 多书并行：跨书检索合成，按书分组展示思考</li>
                            <li>📡 SSE 真流式：token 级前端实时呈现</li>
                            <li>🧰 LangChain 工具链：可见的工具调用与阶段进度</li>
                        </ul>
                    </div>
                </section>
            </div>

            <section class="info-quick">
                <h4>🚀 快速开始</h4>
                <ol class="steps">
                    <li><span class="badge">1</span> 在左侧选择一本书，或切换到 <span class="pill">跨书模式</span> 多选书本</li>
                    <li><span class="badge">2</span> 在下方输入框直接提问或创作指令</li>
                    <li><span class="badge">3</span> 需要修饰输出时，点击消息下方 <span class="pill">润色</span> 或 <span class="pill">点评</span> 按钮</li>
                </ol>
                <div class="chips">
                    <span class="chip" onclick="useExample('这本书的主要人物有哪些？')">主要人物</span>
                    <span class="chip" onclick="useExample('分析一下主人公的性格特点')">性格分析</span>
                    <span class="chip" onclick="useExample('书中的核心冲突是什么？')">核心冲突</span>
                    <span class="chip" onclick="useExample('续写：在第十章之后，描写主角与X重逢')">续写示例</span>
                </div>
            </section>

            <section class="info-tips">
                <h4>💡 使用技巧</h4>
                <ul class="tips-list compact">
                    <li><strong>🎯 具体明确：</strong>尽量给出目标风格、篇幅、禁忌等约束</li>
                    <li><strong>🧩 分阶段：</strong>需要证据时先检索，再让AI基于证据生成</li>
                    <li><strong>🛑 随时停止：</strong>生成太长时可中断并继续润色/改写</li>
                </ul>
            </section>

            <div class="info-actions">
                <button class="quick-action-btn" onclick="listBooks()"><i class="fas fa-list"></i> 查看书籍</button>
                <button class="quick-action-btn" onclick="showAddBookModal()"><i class="fas fa-plus"></i> 添加书籍</button>
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

// === 跨书模式：按书分组的思考过程 ===
function ensureBookThinkingSection(bookName) {
    if (!elements.thinkingSteps) return null;
    const sectionId = `book-steps-${bookName}`;
    let section = document.getElementById(sectionId);
    if (!section) {
        // 外层容器
        section = document.createElement('div');
        section.id = sectionId;
        section.className = 'thinking-step';

        // 头部（可折叠）
        const header = document.createElement('div');
        header.className = 'step-header';
        header.innerHTML = `<span class="step-title">📚 ${bookName}</span><span class="step-time"></span>`;
        section.appendChild(header);

        // 列表容器
        const list = document.createElement('div');
        list.className = 'book-steps-list';
        section.appendChild(list);

        // 点击折叠/展开
        header.addEventListener('click', () => {
            const isHidden = list.style.display === 'none';
            list.style.display = isHidden ? 'block' : 'none';
        });

        elements.thinkingSteps.appendChild(section);
    }
    return section.querySelector('.book-steps-list');
}

function addThinkingStepTo(containerEl, type, title, content) {
    if (!containerEl) return;
    const time = new Date().toLocaleTimeString();
    const stepDiv = document.createElement('div');
    stepDiv.className = `thinking-step thinking-step-${type}`;
    stepDiv.innerHTML = `
        <div class="step-header">
            <span class="step-title">${title}</span>
            <span class="step-time">${time}</span>
        </div>
        <div class="step-content">${content || ''}</div>
    `;
    containerEl.appendChild(stepDiv);
    containerEl.scrollTop = containerEl.scrollHeight;
}

function addThinkingStepForBook(bookName, type, title, content) {
    const list = ensureBookThinkingSection(bookName);
    addThinkingStepTo(list, type, title, content);
}

// 进度条相关函数
function initializeProgress() {
    currentProgress = {
        percentage: 0,
        currentStep: 0,
        totalSteps: 5, // 默认5个步骤
        steps: [
            { name: '理解问题', status: 'pending', icon: '🎯' },
            { name: '检索信息', status: 'pending', icon: '🔍' },
            { name: 'AI推理', status: 'pending', icon: '🤖' },
            { name: '生成回答', status: 'pending', icon: '✍️' },
            { name: '完成输出', status: 'pending', icon: '🎉' }
        ],
        startTime: Date.now(),
        estimatedTime: null
    };
    
    showProgressBar();
    updateProgressBar();
}

function showProgressBar() {
    if (!elements.thinkingSteps) return;
    
    // 检查是否已存在进度条
    let progressContainer = elements.thinkingSteps.querySelector('.progress-container');
    if (!progressContainer) {
        progressContainer = document.createElement('div');
        progressContainer.className = 'progress-container';
        progressContainer.innerHTML = `
            <div class="progress-header">
                <div class="progress-title">
                    <i class="fas fa-tasks"></i>
                    <span>处理进度</span>
                </div>
                <div class="progress-info">
                    <span class="progress-percentage">0%</span>
                    <span class="progress-time"></span>
                </div>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar" style="width: 0%"></div>
            </div>
            <div class="progress-steps"></div>
        `;
        
        // 插入到思考步骤的最前面
        elements.thinkingSteps.insertBefore(progressContainer, elements.thinkingSteps.firstChild);
    }
}

function updateProgressBar() {
    const progressContainer = elements.thinkingSteps?.querySelector('.progress-container');
    if (!progressContainer) return;
    
    const progressBar = progressContainer.querySelector('.progress-bar');
    const progressPercentage = progressContainer.querySelector('.progress-percentage');
    const progressTime = progressContainer.querySelector('.progress-time');
    const progressStepsContainer = progressContainer.querySelector('.progress-steps');
    
    // 更新进度条
    if (progressBar) {
        progressBar.style.width = `${currentProgress.percentage}%`;
        if (currentProgress.percentage >= 100) {
            progressBar.classList.add('completed');
        }
    }
    
    // 更新百分比
    if (progressPercentage) {
        progressPercentage.textContent = `${Math.round(currentProgress.percentage)}%`;
    }
    
    // 更新时间信息
    if (progressTime && currentProgress.startTime) {
        const elapsed = Date.now() - currentProgress.startTime;
        const elapsedSeconds = Math.floor(elapsed / 1000);
        
        if (currentProgress.estimatedTime && currentProgress.percentage > 0) {
            const remaining = Math.max(0, currentProgress.estimatedTime - elapsedSeconds);
            progressTime.textContent = `剩余 ${remaining}s`;
        } else {
            progressTime.textContent = `已用 ${elapsedSeconds}s`;
        }
    }
    
    // 更新步骤指示器
    if (progressStepsContainer) {
        progressStepsContainer.innerHTML = currentProgress.steps.map((step, index) => {
            let className = 'progress-step';
            if (step.status === 'completed') className += ' completed';
            else if (step.status === 'current') className += ' current';
            else className += ' pending';
            
            return `
                <div class="${className}">
                    <span>${step.icon}</span>
                    <span>${step.name}</span>
                </div>
            `;
        }).join('');
    }
}

function updateProgress(stepName, status = 'current') {
    // 查找对应的步骤
    const stepIndex = currentProgress.steps.findIndex(step => 
        step.name === stepName || step.name.includes(stepName) || stepName.includes(step.name)
    );
    
    if (stepIndex !== -1) {
        // 更新当前步骤状态
        currentProgress.steps[stepIndex].status = status;
        currentProgress.currentStep = stepIndex;
        
        // 将之前的步骤标记为完成
        for (let i = 0; i < stepIndex; i++) {
            if (currentProgress.steps[i].status !== 'completed') {
                currentProgress.steps[i].status = 'completed';
            }
        }
        
        // 计算进度百分比
        const completedSteps = currentProgress.steps.filter(step => step.status === 'completed').length;
        const currentStepProgress = status === 'completed' ? 1 : 0.5; // 当前步骤算50%完成
        currentProgress.percentage = Math.min(100, ((completedSteps + currentStepProgress) / currentProgress.totalSteps) * 100);
        
        // 估算剩余时间
        if (currentProgress.percentage > 10) {
            const elapsed = Date.now() - currentProgress.startTime;
            const estimatedTotal = (elapsed / currentProgress.percentage) * 100;
            currentProgress.estimatedTime = Math.floor(estimatedTotal / 1000);
        }
    }
    
    updateProgressBar();
}

function completeProgress() {
    currentProgress.percentage = 100;
    currentProgress.steps.forEach(step => step.status = 'completed');
    updateProgressBar();
    
    // 3秒后隐藏进度条
    setTimeout(() => {
        const progressContainer = elements.thinkingSteps?.querySelector('.progress-container');
        if (progressContainer) {
            progressContainer.style.opacity = '0.5';
            progressContainer.style.transition = 'opacity 0.5s ease';
        }
    }, 3000);
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
    const modeMenuBtn = document.getElementById('modeMenuBtn');
    const modeMenu = document.getElementById('modeMenu');
    const modeDropdown = document.getElementById('modeDropdown');
    const modeMenuBtnOriginalClass = modeMenuBtn ? modeMenuBtn.className : '';
    const selectBooksBtn = elements.selectBooksBtn;
    if (modeMenuBtn && modeDropdown && modeMenu) {
        modeMenuBtn.addEventListener('click', () => {
            modeDropdown.classList.toggle('open');
        });
        modeMenu.querySelectorAll('.dropdown-item').forEach(item => {
            item.addEventListener('click', () => {
                const mode = item.getAttribute('data-mode');
                composeMode = mode === 'cross' ? 'cross' : 'single';
                if (selectBooksBtn) selectBooksBtn.style.display = composeMode === 'cross' ? 'inline-flex' : 'none';
                // 顶栏按钮高亮当前模式
                if (modeMenuBtn) {
                    if (composeMode === 'cross') {
                        modeMenuBtn.classList.add('active');
                    } else {
                        modeMenuBtn.classList.remove('active');
                    }
                }
                // 用 assistant 角色更友好（带机器人图标），避免系统消息的感叹号样式
                addMessage('assistant', composeMode === 'cross' ? '🧩 跨书模式已启用（请选择多本书）' : '📖 单书模式已启用');
                modeDropdown.classList.remove('open');
                // 切换后刷新书单高亮与顶部选择展示
                listBooks();
                updateCurrentSelectionDisplay();
            });
        });
        document.addEventListener('click', (e) => {
            if (!modeDropdown.contains(e.target)) modeDropdown.classList.remove('open');
        });
    }
    if (selectBooksBtn) {
        selectBooksBtn.addEventListener('click', showCrossBookSelector);
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
            thinkingSteps: document.getElementById('thinkingSteps'),
            modeToggleBtn: document.getElementById('modeToggleBtn'),
            selectBooksBtn: document.getElementById('selectBooksBtn')
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
window.polishLastAssistantMessage = polishLastAssistantMessage;
window.polishMessageById = polishMessageById;
window.critiqueMessageById = critiqueMessageById;

// === 润色/点评逻辑 ===
function getLastAssistantMessageWithIndex() {
    for (let i = chatHistory.length - 1; i >= 0; i--) {
        if (chatHistory[i].type === 'assistant' && chatHistory[i].content) {
            return { msg: chatHistory[i], index: i };
        }
    }
    return { msg: null, index: -1 };
}

function getPrevUserPrompt(beforeIndex) {
    if (beforeIndex <= 0) return '';
    for (let i = beforeIndex - 1; i >= 0; i--) {
        const m = chatHistory[i];
        if (m && m.type === 'user' && typeof m.content === 'string' && m.content.trim().length > 0) {
            return m.content;
        }
    }
    return '';
}

async function polishLastAssistantMessage() {
    const { msg: last, index } = getLastAssistantMessageWithIndex();
    if (!last) {
        addMessage('system', '暂无可润色的回答，请先让AI生成一条回答。');
        return;
    }
    const triggeringUserPrompt = getPrevUserPrompt(index);

    // 追加一条"润色中"的消息
    const polishMsgId = 'polish-' + Date.now();
    const polishEl = renderMessage('assistant', '✨ 正在润色上一条回答...', null, polishMsgId);

    // 组织历史为简单数组（复用已有 chatHistory）
    const payload = {
        draft: last.content,
        history: chatHistory.slice(-10),
        userPrompt: triggeringUserPrompt,
        tone: 'neutral',
        targetLength: 'original',
        stream: true
    };

    try {
        const controller = new AbortController();
        const res = await fetch('/api/polish', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: controller.signal
        });
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`润色请求失败: ${res.status} ${text}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentEvent = null;
        let streamingText = '';

        const textDiv = document.getElementById(polishMsgId)?.querySelector('.message-text');
        if (textDiv) textDiv.innerHTML = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            buffer += chunk;
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith('event: ')) {
                    currentEvent = line.slice(7);
                } else if (line.startsWith('data: ') && currentEvent) {
                    const data = line.slice(6);
                    if (!data.trim()) continue;
                    if (currentEvent === 'llm_token') {
                        try {
                            const { token } = JSON.parse(data);
                            if (typeof token === 'string' && token.length > 0) {
                                streamingText += token;
                                if (textDiv) {
                                    textDiv.innerHTML = formatMessage(streamingText);
                                    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
                                }
                            }
                        } catch {}
                    } else if (currentEvent === 'final') {
                        try {
                            const { result } = JSON.parse(data);
                            if (result && textDiv) {
                                textDiv.innerHTML = formatMessage(result);
                            }
                            // 保存到历史
                            chatHistory.push({
                                type: 'assistant',
                                content: result || streamingText,
                                timestamp: new Date().toISOString(),
                                id: polishMsgId,
                                toolCalls: null
                            });
                            saveChatHistory();
                        } catch {}
                    }
                } else if (line === '') {
                    currentEvent = null;
                }
            }
        }
    } catch (err) {
        console.error('润色失败:', err);
        addMessage('system', '❌ 润色失败：' + err.message);
    }
}

async function polishCurrentInput() {
    const draft = elements.messageInput?.value?.trim();
    if (!draft) {
        addMessage('system', '请输入需要润色的文本');
        return;
    }
    const polishMsgId = 'polish-' + Date.now();
    const polishEl = renderMessage('assistant', '✨ 正在润色输入内容...', null, polishMsgId);

    const payload = {
        draft,
        history: chatHistory.slice(-10),
        tone: 'neutral',
        targetLength: 'original',
        stream: true
    };
    try {
        const res = await fetch('/api/polish', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            const t = await res.text();
            throw new Error(`润色请求失败: ${res.status} ${t}`);
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentEvent = null;
        let streamingText = '';
        const textDiv = document.getElementById(polishMsgId)?.querySelector('.message-text');
        if (textDiv) textDiv.innerHTML = '';
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            buffer += chunk;
            const lines = buffer.split('\n');
            buffer = lines.pop();
            for (const line of lines) {
                if (line.startsWith('event: ')) {
                    currentEvent = line.slice(7);
                } else if (line.startsWith('data: ') && currentEvent) {
                    const data = line.slice(6);
                    if (!data.trim()) continue;
                    if (currentEvent === 'llm_token') {
                        try {
                            const { token } = JSON.parse(data);
                            if (typeof token === 'string' && token.length > 0) {
                                streamingText += token;
                                if (textDiv) {
                                    textDiv.innerHTML = formatMessage(streamingText);
                                    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
                                }
                            }
                        } catch {}
                    } else if (currentEvent === 'final') {
                        try {
                            const { result } = JSON.parse(data);
                            if (result && textDiv) textDiv.innerHTML = formatMessage(result);
                            chatHistory.push({
                                type: 'assistant',
                                content: result || streamingText,
                                timestamp: new Date().toISOString(),
                                id: polishMsgId,
                                toolCalls: null
                            });
                            saveChatHistory();
                        } catch {}
                    }
                } else if (line === '') {
                    currentEvent = null;
                }
            }
        }
    } catch (e) {
        console.error('润色失败:', e);
        addMessage('system', '❌ 润色失败：' + e.message);
    }
}

// 根据消息ID执行润色：抓取该ID消息文本，以及其前一条用户prompt
async function polishMessageById(targetId) {
    const idx = chatHistory.findIndex(m => m.id === targetId);
    if (idx === -1) {
        addMessage('system', '找不到目标消息，无法润色');
        return;
    }
    const draft = chatHistory[idx].content || '';
    const userPrompt = getPrevUserPrompt(idx);
    if (!draft) {
        addMessage('system', '该回复为空，无法润色');
        return;
    }
    
    // 为润色按钮添加激活状态 - 改进查找机制
    const targetMessageEl = document.querySelector(`[data-message-id="${targetId}"]`) || 
                           document.getElementById(targetId);
    let polishBtn = null;
    if (targetMessageEl) {
        polishBtn = targetMessageEl.querySelector('.icon-btn[title="润色"]');
    }
    if (polishBtn) {
        polishBtn.classList.add('polish-active');
    }
    
    const outId = 'polish-' + Date.now();
    const el = renderMessage('assistant',
        `<div class="magic-wrapper">
            <div class="magic-loading">
                <span class="magic-star"><i class="fas fa-star"></i></span>
                <span class="magic-text">正在施展润色魔法，可能需要一点时间<span class="magic-dots"></span></span>
            </div>
            <div class="magic-stream" style="display:none;">
                <div class="magic-diff-hint">
                    <i class="fas fa-eye"></i>
                    <span>润色高亮说明：<span class="diff-added" style="margin:0 4px;">绿色</span>为新增内容，<span class="diff-modified" style="margin:0 4px;">黄色</span>为修改内容</span>
                </div>
                <div class="polish-content"></div>
            </div>
        </div>`,
        null,
        outId
    );
    
    try {
        await streamPolish({ draft, userPrompt, outId });
    } finally {
        // 移除润色按钮的激活状态
        if (polishBtn) {
            polishBtn.classList.remove('polish-active');
        }
    }
}

// 修改意见（点评）按钮：针对某条回复输出详细改进建议
async function critiqueMessageById(targetId) {
    const idx = chatHistory.findIndex(m => m.id === targetId);
    if (idx === -1) {
        addMessage('system', '找不到目标消息，无法给出建议');
        return;
    }
    const text = chatHistory[idx].content || '';
    const userPrompt = getPrevUserPrompt(idx);
    if (!text) {
        addMessage('system', '该回复为空，无法给出建议');
        return;
    }
    const outId = 'critique-' + Date.now();
    const el = renderMessage('assistant',
        `<div class="magic-wrapper">
            <div class="magic-loading">
                <span class="magic-star"><i class="fas fa-star"></i></span>
                <span class="magic-text">正在施展点评魔法，可能需要一点时间<span class="magic-dots"></span></span>
            </div>
            <div class="magic-stream" style="display:none;"></div>
        </div>`,
        null,
        outId
    );
    await streamCritique({ text, userPrompt, outId });
}

// 封装：以SSE流式调用 /api/polish
async function streamPolish({ draft, userPrompt = '', outId }) {
    const payload = {
        draft,
        userPrompt,
        history: chatHistory.slice(-10),
        tone: 'neutral',
        targetLength: 'original',
        stream: true
    };
    await sseToMessage({ url: '/api/polish', payload, outId, originalText: draft });
}

// 封装：以SSE流式调用 /api/critique
async function streamCritique({ text, userPrompt = '', outId }) {
    const payload = {
        text,
        userPrompt,
        history: chatHistory.slice(-10),
        stream: true
    };
    await sseToMessage({ url: '/api/critique', payload, outId });
}

// 通用SSE到消息渲染
async function sseToMessage({ url, payload, outId, originalText = null }) {
    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            const t = await res.text();
            throw new Error(`${url} 请求失败: ${res.status} ${t}`);
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentEvent = null;
        let streamingText = '';
        const wrapper = document.getElementById(outId)?.querySelector('.message-text');
        let streamDiv = null;
        let loadingDiv = null;
        let polishContentDiv = null;
        if (wrapper) {
            // 使用占位结构：magic-wrapper > magic-loading + magic-stream
            const w = wrapper.querySelector('.magic-wrapper');
            if (w) {
                loadingDiv = w.querySelector('.magic-loading');
                streamDiv = w.querySelector('.magic-stream');
                polishContentDiv = w.querySelector('.polish-content');
            }
        }
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            buffer += chunk;
            const lines = buffer.split('\n');
            buffer = lines.pop();
            for (const line of lines) {
                if (line.startsWith('event: ')) {
                    currentEvent = line.slice(7);
                } else if (line.startsWith('data: ') && currentEvent) {
                    const data = line.slice(6);
                    if (!data.trim()) continue;
                    if (currentEvent === 'llm_token') {
                        try {
                            const { token } = JSON.parse(data);
                            if (typeof token === 'string' && token.length > 0) {
                                streamingText += token;
                                if (wrapper) {
                                    if (loadingDiv && streamDiv && streamDiv.style.display === 'none') {
                                        // 首次收到token：显示正文区域，隐藏加载动画
                                        loadingDiv.style.display = 'none';
                                        streamDiv.style.display = 'block';
                                    }
                                    // 如果是润色功能且有原文，显示diff高亮
                                    if (originalText && url === '/api/polish') {
                                        if (polishContentDiv) {
                                            polishContentDiv.innerHTML = formatMessageWithDiff(originalText, streamingText);
                                        } else if (streamDiv) {
                                            streamDiv.innerHTML = formatMessageWithDiff(originalText, streamingText);
                                        }
                                    } else {
                                        if (polishContentDiv) {
                                            polishContentDiv.innerHTML = formatMessage(streamingText);
                                        } else if (streamDiv) {
                                            streamDiv.innerHTML = formatMessage(streamingText);
                                        }
                                    }
                                    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
                                }
                            }
                        } catch {}
                    } else if (currentEvent === 'final') {
                        try {
                            const obj = JSON.parse(data);
                            const finalText = obj.result || obj.critique || streamingText;
                            if (wrapper) {
                                if (loadingDiv) loadingDiv.style.display = 'none';
                                if (streamDiv) {
                                    streamDiv.style.display = 'block';
                                    // 如果是润色功能且有原文，显示diff高亮
                                    if (originalText && url === '/api/polish') {
                                        if (polishContentDiv) {
                                            polishContentDiv.innerHTML = formatMessageWithDiff(originalText, finalText);
                                        } else {
                                            streamDiv.innerHTML = formatMessageWithDiff(originalText, finalText);
                                        }
                                    } else {
                                        if (polishContentDiv) {
                                            polishContentDiv.innerHTML = formatMessage(finalText);
                                        } else {
                                            streamDiv.innerHTML = formatMessage(finalText);
                                        }
                                    }
                                } else {
                                    wrapper.innerHTML = formatMessage(finalText);
                                }
                            }
                            chatHistory.push({
                                type: 'assistant',
                                content: finalText,
                                timestamp: new Date().toISOString(),
                                id: outId,
                                toolCalls: null
                            });
                            saveChatHistory();
                        } catch {}
                    }
                } else if (line === '') {
                    currentEvent = null;
                }
            }
        }
    } catch (e) {
        console.error('SSE失败:', e);
        addMessage('system', '❌ 请求失败：' + e.message);
    }
}