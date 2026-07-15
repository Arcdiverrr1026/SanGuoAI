document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const configForm = document.getElementById('config-form');
    const saveConfigBtn = document.getElementById('save-config-btn');
    const rebuildIndexBtn = document.getElementById('rebuild-index-btn');
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    const sendBtn = document.getElementById('send-btn');
    
    const sidebar = document.getElementById('sidebar');
    const menuToggle = document.getElementById('menu-toggle');
    const referencesPanel = document.getElementById('references-panel');
    const refToggle = document.getElementById('ref-toggle');
    const panelClose = document.getElementById('panel-close');
    const refCount = document.getElementById('ref-count');
    const referencesList = document.getElementById('references-list');

    // Document Upload Elements
    const kbFileInput = document.getElementById('kb-file-input');
    const kbUploadBtn = document.getElementById('kb-upload-btn');

    // Right Panel Tab Elements
    const tabRefBtn = document.getElementById('tab-ref-btn');
    const tabFavBtn = document.getElementById('tab-fav-btn');
    const tabRefContent = document.getElementById('tab-ref-content');
    const tabFavContent = document.getElementById('tab-fav-content');
    const favoritesList = document.getElementById('favorites-list');

    // State Variables
    let isRebuilding = false;
    let lastUserQuestion = ""; // Tracks the last submitted user question for bookmarking

    // Toast Notification helper
    function showToast(message, isError = false) {
        const toast = document.createElement('div');
        toast.className = `toast ${isError ? 'error' : ''}`;
        toast.innerText = message;
        document.body.appendChild(toast);
        
        // Force reflow
        toast.offsetHeight;
        
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3000);
    }

    // Toggle Sidebars
    menuToggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
    });

    refToggle.addEventListener('click', () => {
        referencesPanel.classList.toggle('collapsed');
    });

    panelClose.addEventListener('click', () => {
        referencesPanel.classList.add('collapsed');
    });

    // Close sidebar on click outside in mobile view
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 900) {
            if (!sidebar.contains(e.target) && e.target !== menuToggle) {
                sidebar.classList.remove('open');
            }
        }
    });

    // Right Panel Tabs Navigation
    tabRefBtn.addEventListener('click', () => {
        tabRefBtn.classList.add('active');
        tabRefBtn.style.color = 'var(--primary-light)';
        tabRefBtn.style.borderBottom = '2px solid var(--primary-light)';
        
        tabFavBtn.classList.remove('active');
        tabFavBtn.style.color = 'var(--text-muted)';
        tabFavBtn.style.borderBottom = 'none';
        
        tabRefContent.style.display = 'flex';
        tabFavContent.style.display = 'none';
    });

    tabFavBtn.addEventListener('click', () => {
        tabFavBtn.classList.add('active');
        tabFavBtn.style.color = 'var(--primary-light)';
        tabFavBtn.style.borderBottom = '2px solid var(--primary-light)';
        
        tabRefBtn.classList.remove('active');
        tabRefBtn.style.color = 'var(--text-muted)';
        tabRefBtn.style.borderBottom = 'none';
        
        tabRefContent.style.display = 'none';
        tabFavContent.style.display = 'flex';
        
        fetchFavorites();
    });

    // KB File Upload Handling
    kbUploadBtn.addEventListener('click', () => {
        kbFileInput.click();
    });

    kbFileInput.addEventListener('change', async () => {
        const file = kbFileInput.files[0];
        if (!file) return;

        if (!file.name.endsWith('.txt')) {
            showToast('仅支持上传 .txt 格式的文本文件！', true);
            kbFileInput.value = '';
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        kbUploadBtn.disabled = true;
        kbUploadBtn.innerText = '正在上传并索引...';

        try {
            const response = await fetch('/api/kb/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '上传文件失败');
            }

            showToast('文献上传成功，知识库已重构完毕！');
            fetchKbStatus();
            checkIndexStatus();
        } catch (error) {
            showToast(error.message, true);
        } finally {
            kbUploadBtn.disabled = false;
            kbUploadBtn.innerText = '📂 上传新文献 (.txt)';
            kbFileInput.value = '';
        }
    });

    // Fetch and populate configuration
    async function fetchConfig() {
        try {
            const response = await fetch('/api/config');
            if (!response.ok) throw new Error('获取配置失败');
            const data = await response.json();
            
            // Populate LLM
            document.getElementById('llm-provider').value = data.llm.provider;
            document.getElementById('llm-model').value = data.llm.model;
            document.getElementById('llm-api-key').value = data.llm.api_key;
            document.getElementById('llm-api-base').value = data.llm.api_base;
            document.getElementById('llm-temperature').value = data.llm.temperature;
            document.getElementById('llm-top-p').value = data.llm.top_p;
            
            // Populate Embedding
            document.getElementById('embed-provider').value = data.embedding.provider;
            document.getElementById('embed-model').value = data.embedding.model;
            document.getElementById('embed-api-key').value = data.embedding.api_key;
            document.getElementById('embed-api-base').value = data.embedding.api_base;
            
            // Populate RAG
            document.getElementById('rag-chunk-size').value = data.rag.chunk_size;
            document.getElementById('rag-chunk-overlap').value = data.rag.chunk_overlap;
            document.getElementById('rag-top-k').value = data.rag.similarity_top_k;
            document.getElementById('rag-prompt').value = data.rag.system_prompt;
            
            checkIndexStatus();
            fetchKbStatus();
        } catch (error) {
            showToast(error.message, true);
        }
    }

    // Check Index status
    async function checkIndexStatus() {
        if (isRebuilding) return;
        
        try {
            const response = await fetch('/api/index/status');
            if (!response.ok) throw new Error('获取索引状态失败');
            const data = await response.json();
            
            if (data.exists) {
                statusIndicator.className = 'status-indicator ready';
                statusText.innerText = '向量索引就绪';
            } else {
                statusIndicator.className = 'status-indicator';
                statusText.innerText = '未检测到索引，请点击保存或重建';
            }
            fetchKbStatus(); // Also update counts
        } catch (error) {
            statusIndicator.className = 'status-indicator';
            statusText.innerText = '检测状态出错';
        }
    }

    // Fetch and populate KB and vector store status
    async function fetchKbStatus() {
        try {
            const response = await fetch('/api/kb/status');
            if (!response.ok) throw new Error('获取知识库状态失败');
            const data = await response.json();
            
            // Render files list
            const fileListEl = document.getElementById('status-file-list');
            fileListEl.innerHTML = '';
            
            if (data.files && data.files.length > 0) {
                data.files.forEach(file => {
                    const li = document.createElement('li');
                    li.style.color = '#e5e7eb';
                    li.style.display = 'flex';
                    li.style.justifyContent = 'space-between';
                    li.style.background = 'rgba(255,255,255,0.02)';
                    li.style.padding = '4px 8px';
                    li.style.borderRadius = '4px';
                    li.style.border = '1px solid rgba(255,255,255,0.04)';
                    
                    const nameSpan = document.createElement('span');
                    nameSpan.innerText = `📄 ${file.name}`;
                    
                    const sizeSpan = document.createElement('span');
                    sizeSpan.style.color = 'var(--text-muted)';
                    sizeSpan.innerText = `${file.size_kb} KB`;
                    
                    li.appendChild(nameSpan);
                    li.appendChild(sizeSpan);
                    fileListEl.appendChild(li);
                });
            } else {
                fileListEl.innerHTML = '<li style="color: var(--text-muted);">暂无核心文献</li>';
            }
            
            // Render vector count & path
            document.getElementById('status-vector-count').innerText = data.active_index.vector_count;
            
            const fullPath = data.active_index.path || '暂无';
            const pathParts = fullPath.split('/');
            const displayPath = pathParts[pathParts.length - 1] || fullPath;
            document.getElementById('status-vector-path').innerText = displayPath;
            document.getElementById('status-vector-path').title = fullPath;
        } catch (error) {
            console.error('KB status error:', error);
        }
    }

    // Fetch and populate favorites
    async function fetchFavorites() {
        try {
            const response = await fetch('/api/favorites');
            if (!response.ok) throw new Error('获取收藏列表失败');
            const data = await response.json();
            
            favoritesList.innerHTML = '';
            
            if (data && data.length > 0) {
                data.forEach((fav) => {
                    const card = document.createElement('div');
                    card.className = 'ref-card';
                    card.style.borderLeft = '3px solid var(--primary)';
                    
                    const header = document.createElement('div');
                    header.className = 'ref-card-header';
                    
                    const titleSpan = document.createElement('span');
                    titleSpan.className = 'ref-source';
                    titleSpan.style.background = 'rgba(217, 119, 6, 0.15)';
                    titleSpan.style.color = 'var(--primary-light)';
                    titleSpan.innerText = `⭐ 收藏妙计`;
                    
                    const delBtn = document.createElement('button');
                    delBtn.type = 'button';
                    delBtn.style.background = 'none';
                    delBtn.style.border = 'none';
                    delBtn.style.color = '#ef4444';
                    delBtn.style.fontSize = '11px';
                    delBtn.style.cursor = 'pointer';
                    delBtn.innerText = '❌ 移除';
                    
                    delBtn.addEventListener('click', async () => {
                        if (confirm('确定要删除这条收藏吗？')) {
                            try {
                                const res = await fetch(`/api/favorites/${fav.id}`, { method: 'DELETE' });
                                if (!res.ok) throw new Error('删除失败');
                                showToast('已成功移除收藏！');
                                fetchFavorites();
                            } catch (err) {
                                showToast(err.message, true);
                            }
                        }
                    });
                    
                    header.appendChild(titleSpan);
                    header.appendChild(delBtn);
                    
                    const textContent = document.createElement('div');
                    textContent.className = 'ref-text';
                    textContent.innerHTML = `<strong>问：</strong>${fav.question}<br><strong style="color:var(--primary-light);">答：</strong>${formatMessageText(fav.answer)}`;
                    
                    card.appendChild(header);
                    card.appendChild(textContent);
                    favoritesList.appendChild(card);
                });
            } else {
                favoritesList.innerHTML = '<div class="no-favorites" style="text-align: center; color: var(--text-muted); font-size: 12.5px; margin-top: 40px;">暂无收藏。在回答框点击“⭐ 收藏此策”即可保存。</div>';
            }
        } catch (error) {
            console.error('Favorites status error:', error);
        }
    }

    // Save and apply settings
    saveConfigBtn.addEventListener('click', async () => {
        const settings = {
            "llm.provider": document.getElementById('llm-provider').value,
            "llm.model": document.getElementById('llm-model').value,
            "llm.api_key": document.getElementById('llm-api-key').value,
            "llm.api_base": document.getElementById('llm-api-base').value,
            "llm.temperature": document.getElementById('llm-temperature').value,
            "llm.top_p": document.getElementById('llm-top-p').value,
            
            "embedding.provider": document.getElementById('embed-provider').value,
            "embedding.model": document.getElementById('embed-model').value,
            "embedding.api_key": document.getElementById('embed-api-key').value,
            "embedding.api_base": document.getElementById('embed-api-base').value,
            
            "rag.chunk_size": document.getElementById('rag-chunk-size').value,
            "rag.chunk_overlap": document.getElementById('rag-chunk-overlap').value,
            "rag.similarity_top_k": document.getElementById('rag-top-k').value,
            "rag.system_prompt": document.getElementById('rag-prompt').value,
        };

        saveConfigBtn.disabled = true;
        saveConfigBtn.innerText = '正在保存并应用...';
        
        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ settings })
            });
            
            if (!response.ok) throw new Error('保存配置失败');
            showToast('配置保存并应用成功！');
            checkIndexStatus();
        } catch (error) {
            showToast(error.message, true);
        } finally {
            saveConfigBtn.disabled = false;
            saveConfigBtn.innerText = '保存并应用配置';
        }
    });

    // Force rebuild index
    rebuildIndexBtn.addEventListener('click', async () => {
        if (!confirm('重建向量索引需要重新计算所有分片的向量。是否继续？')) {
            return;
        }
        
        isRebuilding = true;
        rebuildIndexBtn.disabled = true;
        rebuildIndexBtn.innerText = '正在构建索引...';
        statusIndicator.className = 'status-indicator loading';
        statusText.innerText = '正在构建向量索引，请稍候...';
        
        try {
            const response = await fetch('/api/index/rebuild', { method: 'POST' });
            if (!response.ok) throw new Error('重建索引失败');
            showToast('向量索引重建完成！');
        } catch (error) {
            showToast(error.message, true);
        } finally {
            isRebuilding = false;
            rebuildIndexBtn.disabled = false;
            rebuildIndexBtn.innerText = '🧱 重建向量索引';
            checkIndexStatus();
        }
    });

    // Simple markdown formatting helper
    function formatMessageText(text) {
        if (!text) return '';
        
        // Escape HTML to prevent injection
        let escaped = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
            
        // Replace bold **text**
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Replace newlines with <br>
        escaped = escaped.replace(/\n/g, '<br>');
        
        return escaped;
    }

    // Append chat message to the panel
    function appendMessage(sender, text, avatar = '👤') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'avatar';
        avatarDiv.innerText = avatar;
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        if (sender === 'system') {
            bubble.innerHTML = formatMessageText(text);
            
            // Add Favorite action button for assistant responses
            const actionDiv = document.createElement('div');
            actionDiv.className = 'message-actions';
            actionDiv.style.display = 'flex';
            actionDiv.style.justifyContent = 'flex-end';
            actionDiv.style.marginTop = '8px';
            actionDiv.style.borderTop = '1px dashed rgba(217, 119, 6, 0.15)';
            actionDiv.style.paddingTop = '6px';
            
            const favBtn = document.createElement('button');
            favBtn.type = 'button';
            favBtn.className = 'msg-fav-btn';
            favBtn.style.background = 'none';
            favBtn.style.border = 'none';
            favBtn.style.color = 'var(--primary-light)';
            favBtn.style.fontSize = '11px';
            favBtn.style.cursor = 'pointer';
            favBtn.style.display = 'flex';
            favBtn.style.alignItems = 'center';
            favBtn.style.gap = '4px';
            favBtn.style.fontWeight = '600';
            favBtn.innerHTML = '⭐ 收藏此策';
            
            favBtn.addEventListener('click', async () => {
                favBtn.disabled = true;
                favBtn.innerHTML = '⚡ 正在保存...';
                
                try {
                    const res = await fetch('/api/favorites', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            question: lastUserQuestion || "主公之问",
                            answer: text
                        })
                    });
                    if (!res.ok) throw new Error('收藏失败');
                    showToast('妙计已成功收入秘策阁！');
                    favBtn.innerHTML = '✅ 已收藏';
                    fetchFavorites(); // Refresh favorites tab list
                } catch (err) {
                    showToast(err.message, true);
                    favBtn.disabled = false;
                    favBtn.innerHTML = '⭐ 收藏此策';
                }
            });
            
            actionDiv.appendChild(favBtn);
            bubble.appendChild(actionDiv);
        } else {
            const p = document.createElement('p');
            p.innerText = text;
            bubble.appendChild(p);
        }
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(bubble);
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return messageDiv;
    }

    // Handle Question Submission
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = userInput.value.trim();
        if (!text) return;
        
        // Disable inputs
        userInput.disabled = true;
        sendBtn.disabled = true;
        
        // Track the question for favorites
        lastUserQuestion = text;
        
        // Add User Message
        appendMessage('user', text, '⚔️');
        userInput.value = '';
        
        // Add Typing Indicator
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message system typing-indicator-container';
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'avatar';
        avatarDiv.innerText = '🏯';
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.innerHTML = `
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        
        typingDiv.appendChild(avatarDiv);
        typingDiv.appendChild(bubble);
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: text })
            });
            
            typingDiv.remove();
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '请求失败，请检查配置与网络。');
            }
            
            const data = await response.json();
            
            // Add Assistant Message (show banner if retrieved directly from favorites library)
            if (data.from_favorites) {
                appendMessage('system', `**【✨ 已直接从收藏秘策中召回】**\n\n${data.answer}`, '🏯');
            } else {
                appendMessage('system', data.answer, '🏯');
            }
            
            // Update Reference nodes
            renderReferences(data.sources);
        } catch (error) {
            typingDiv.remove();
            appendMessage('system', `❌ 错误：${error.message}`, '🏯');
            showToast(error.message, true);
        } finally {
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
        }
    });

    // Render retrieved reference nodes
    function renderReferences(sources) {
        referencesList.innerHTML = '';
        
        if (!sources || sources.length === 0) {
            refCount.innerText = '0';
            referencesList.innerHTML = '<div class="no-references">此回答未参考任何特定文档内容（可能未命中知识库）。</div>';
            return;
        }
        
        refCount.innerText = sources.length;
        
        sources.forEach((source, index) => {
            const card = document.createElement('div');
            card.className = 'ref-card';
            
            const header = document.createElement('div');
            header.className = 'ref-card-header';
            
            const sourceName = document.createElement('span');
            sourceName.className = 'ref-source';
            sourceName.innerText = `文献 [${index + 1}] - ${source.file_name}`;
            
            const scoreBadge = document.createElement('span');
            scoreBadge.className = 'ref-score';
            scoreBadge.innerText = source.score !== null ? `匹配度: ${(source.score * 100).toFixed(1)}%` : '匹配度: N/A';
            
            header.appendChild(sourceName);
            header.appendChild(scoreBadge);
            
            const textContent = document.createElement('div');
            textContent.className = 'ref-text';
            textContent.innerText = source.text;
            
            card.appendChild(header);
            card.appendChild(textContent);
            referencesList.appendChild(card);
        });

        // Switch to References tab
        tabRefBtn.click();

        // Automatically expand references panel on first search result
        referencesPanel.classList.remove('collapsed');
    }

    // Initialize application config and fetch favorites list
    fetchConfig();
    fetchFavorites();
});
