/**
 * Ytili AI Chat Widget - Vanilla JavaScript Implementation
 * Floating chat widget with multiple conversation modes
 */

class YtiliChatWidget {
    constructor(options = {}) {
        this.apiBaseUrl = options.apiBaseUrl || '/api/v1';
        this.authToken = options.authToken || null;
        this.position = options.position || 'bottom-right';
        this.defaultMode = options.defaultMode || 'general_support';
        
        this.isOpen = false;
        this.currentMode = this.defaultMode;
        this.showModeSelector = false;
        this.hasNewMessage = false;
        this.isMinimized = false;
        this.chatSession = null;
        this.messages = [];
        
        this.conversationModes = [
            {
                id: 'donation_advisory',
                name: 'Tư vấn quyên góp',
                icon: '❤️',
                color: 'bg-blue-600',
                description: 'Nhận gợi ý quyên góp thông minh dựa trên nhu cầu thực tế'
            },
            {
                id: 'medical_info',
                name: 'Thông tin y tế',
                icon: '🤖',
                color: 'bg-green-600',
                description: 'Thông tin y tế cơ bản và hướng dẫn sức khỏe',
                disclaimer: 'Thông tin chỉ mang tính tham khảo, không thay thế ý kiến bác sĩ'
            },
            {
                id: 'campaign_help',
                name: 'Hỗ trợ chiến dịch',
                icon: '❓',
                color: 'bg-purple-600',
                description: 'Hỗ trợ tạo và quản lý chiến dịch quyên góp'
            },
            {
                id: 'emergency_request',
                name: 'Yêu cầu khẩn cấp',
                icon: '⚠️',
                color: 'bg-red-600',
                description: 'Hỗ trợ khẩn cấp cho các tình huống y tế cấp bách'
            },
            {
                id: 'general_support',
                name: 'Hỗ trợ chung',
                icon: '💬',
                color: 'bg-gray-600',
                description: 'Hỗ trợ chung về nền tảng và các tính năng'
            }
        ];
        
        this.init();
    }
    
    init() {
        this.createWidget();
        this.attachEventListeners();
        this.initSpeechRecognition();
    }
    
    createWidget() {
        // Create widget container
        this.widget = document.createElement('div');
        this.widget.className = 'ytili-chat-widget';
        this.widget.innerHTML = this.getWidgetHTML();

        // Append to body
        document.body.appendChild(this.widget);
    }
    

    
    getWidgetHTML() {
        const currentModeConfig = this.conversationModes.find(mode => mode.id === this.currentMode) || this.conversationModes[4];
        
        return `
            <!-- Mode Selector Popup -->
            <div id="mode-selector" class="ytili-mode-selector hidden">
                <h3 class="fw-semibold text-dark mb-3">Chọn loại hỗ trợ</h3>
                <div class="d-grid gap-2">
                    ${this.conversationModes.map(mode => `
                        <button data-mode="${mode.id}" class="mode-btn btn text-start p-3 border ${
                            this.currentMode === mode.id ? 'border-primary bg-light' : 'border-secondary'
                        }">
                            <div class="d-flex align-items-center">
                                <div class="p-2 rounded-circle text-white ${mode.color} me-3">
                                    ${mode.icon}
                                </div>
                                <div class="flex-grow-1">
                                    <h6 class="fw-medium text-dark mb-1">${mode.name}</h6>
                                    <p class="small text-muted mb-0">${mode.description}</p>
                                    ${mode.disclaimer ? `<p class="small text-warning mt-1">⚠️ ${mode.disclaimer}</p>` : ''}
                                </div>
                            </div>
                        </button>
                    `).join('')}
                </div>
            </div>

            <!-- Emergency SOS Button -->
            <div style="position: absolute; top: -60px; right: 0;">
                <button id="emergency-btn" class="btn bg-red-600 text-white p-3 rounded-circle shadow animate-pulse" title="Yêu cầu khẩn cấp">
                    📞
                </button>
            </div>

            <!-- Chat Window -->
            <div id="chat-window" class="ytili-chat-window hidden">
                <!-- Header -->
                <div class="d-flex align-items-center justify-content-between p-3 border-bottom bg-light rounded-top">
                    <div class="d-flex align-items-center">
                        <div class="p-1 rounded-circle text-white ${currentModeConfig.color} me-2">
                            ${currentModeConfig.icon}
                        </div>
                        <div>
                            <h6 class="fw-medium text-dark mb-0 small">${currentModeConfig.name}</h6>
                            <p class="small text-muted mb-0">Ytili AI Agent</p>
                        </div>
                    </div>
                    <div class="d-flex align-items-center">
                        <button id="mode-toggle" class="btn btn-sm text-muted me-1" title="Đổi chế độ">
                            🤖
                        </button>
                        <button id="minimize-btn" class="btn btn-sm text-muted me-1" title="Thu gọn">
                            💬
                        </button>
                        <button id="close-btn" class="btn btn-sm text-muted" title="Đóng">
                            ✕
                        </button>
                    </div>
                </div>

                <!-- Chat Content -->
                <div id="chat-content" class="flex-grow-1 overflow-hidden">
                    <div id="messages-container" class="p-4" style="height: 320px; overflow-y: auto;">
                        <!-- Messages will be inserted here -->
                    </div>

                    <!-- Input Area -->
                    <div class="border-top p-3">
                        <div class="d-flex align-items-center">
                            <input type="text" id="message-input" placeholder="Nhập tin nhắn của bạn..."
                                   class="form-control me-2">
                            <button id="voice-btn" class="btn btn-outline-secondary me-2" title="Ghi âm">
                                🎤
                            </button>
                            <button id="send-btn" class="btn btn-primary" title="Gửi">
                                ➤
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Floating Button -->
            <button id="chat-toggle" class="btn rounded-circle shadow text-white ${currentModeConfig.color}"
                    style="width: 60px; height: 60px; position: relative;"
                    title="Ytili AI Agent - ${currentModeConfig.name}">
                ${currentModeConfig.icon}

                <!-- New message indicator -->
                <div id="new-message-indicator" class="hidden position-absolute bg-danger rounded-circle animate-ping"
                     style="top: -2px; right: -2px; width: 12px; height: 12px;"></div>

                <!-- Mode indicator -->
                <div class="position-absolute bg-white rounded-circle d-flex align-items-center justify-content-center"
                     style="top: -8px; left: -8px; width: 16px; height: 16px;">
                    <div class="rounded-circle ${currentModeConfig.color}" style="width: 8px; height: 8px;"></div>
                </div>
            </button>
        `;
    }
    
    attachEventListeners() {
        // Chat toggle
        this.widget.querySelector('#chat-toggle').addEventListener('click', () => this.toggleChat());
        
        // Emergency button
        this.widget.querySelector('#emergency-btn').addEventListener('click', () => this.handleEmergencyClick());
        
        // Mode selector
        this.widget.querySelector('#mode-toggle').addEventListener('click', () => this.toggleModeSelector());
        
        // Mode buttons
        this.widget.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const mode = e.currentTarget.getAttribute('data-mode');
                this.changeMode(mode);
            });
        });
        
        // Close and minimize
        this.widget.querySelector('#close-btn').addEventListener('click', () => this.toggleChat());
        this.widget.querySelector('#minimize-btn').addEventListener('click', () => this.toggleMinimize());
        
        // Message input
        const messageInput = this.widget.querySelector('#message-input');
        const sendBtn = this.widget.querySelector('#send-btn');
        
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
        
        sendBtn.addEventListener('click', () => this.sendMessage());
        
        // Voice button
        this.widget.querySelector('#voice-btn').addEventListener('click', () => this.toggleVoiceInput());
        
        // Click outside to close mode selector
        document.addEventListener('click', (e) => {
            if (!this.widget.contains(e.target)) {
                this.hideModeSelector();
            }
        });
    }
    

    
    initSpeechRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = 'vi-VN';

            this.recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                this.widget.querySelector('#message-input').value = transcript;
                this.isListening = false;
                this.updateVoiceButton();
            };

            this.recognition.onerror = () => {
                this.isListening = false;
                this.updateVoiceButton();
                this.showError('Lỗi nhận dạng giọng nói');
            };

            this.recognition.onend = () => {
                this.isListening = false;
                this.updateVoiceButton();
            };
        }
    }

    toggleChat() {
        this.isOpen = !this.isOpen;
        const chatWindow = this.widget.querySelector('#chat-window');

        if (this.isOpen) {
            chatWindow.classList.remove('hidden');
            this.hideModeSelector();
            this.isMinimized = false;
            this.startChatSession();
        } else {
            chatWindow.classList.add('hidden');
        }
    }

    toggleModeSelector() {
        this.showModeSelector = !this.showModeSelector;
        const modeSelector = this.widget.querySelector('#mode-selector');

        if (this.showModeSelector) {
            modeSelector.classList.remove('hidden');
        } else {
            modeSelector.classList.add('hidden');
        }
    }

    hideModeSelector() {
        this.showModeSelector = false;
        this.widget.querySelector('#mode-selector').classList.add('hidden');
    }

    changeMode(modeId) {
        this.currentMode = modeId;
        this.hideModeSelector();

        if (!this.isOpen) {
            this.toggleChat();
        }

        // Update UI
        this.updateModeDisplay();
        this.startChatSession();
    }

    handleEmergencyClick() {
        this.changeMode('emergency_request');
    }

    toggleMinimize() {
        this.isMinimized = !this.isMinimized;
        const chatWindow = this.widget.querySelector('#chat-window');
        const chatContent = this.widget.querySelector('#chat-content');

        if (this.isMinimized) {
            chatWindow.classList.add('minimized');
            chatContent.style.display = 'none';
        } else {
            chatWindow.classList.remove('minimized');
            chatContent.style.display = 'block';
        }
    }

    toggleVoiceInput() {
        if (!this.recognition) {
            this.showError('Trình duyệt không hỗ trợ nhận dạng giọng nói');
            return;
        }

        if (this.isListening) {
            this.recognition.stop();
            this.isListening = false;
        } else {
            this.recognition.start();
            this.isListening = true;
        }

        this.updateVoiceButton();
    }

    updateVoiceButton() {
        const voiceBtn = this.widget.querySelector('#voice-btn');
        if (this.isListening) {
            voiceBtn.innerHTML = '🔴';
            voiceBtn.classList.add('animate-pulse');
        } else {
            voiceBtn.innerHTML = '🎤';
            voiceBtn.classList.remove('animate-pulse');
        }
    }

    updateModeDisplay() {
        const currentModeConfig = this.conversationModes.find(mode => mode.id === this.currentMode) || this.conversationModes[4];

        // Update floating button
        const chatToggle = this.widget.querySelector('#chat-toggle');
        chatToggle.innerHTML = `
            ${currentModeConfig.icon}
            <div id="new-message-indicator" class="hidden position-absolute bg-danger rounded-circle animate-ping"
                 style="top: -2px; right: -2px; width: 12px; height: 12px;"></div>
            <div class="position-absolute bg-white rounded-circle d-flex align-items-center justify-content-center"
                 style="top: -8px; left: -8px; width: 16px; height: 16px;">
                <div class="rounded-circle ${currentModeConfig.color}" style="width: 8px; height: 8px;"></div>
            </div>
        `;
        chatToggle.className = `btn rounded-circle shadow text-white ${currentModeConfig.color}`;
        chatToggle.style.cssText = "width: 60px; height: 60px; position: relative;";
        chatToggle.title = `Ytili AI Agent - ${currentModeConfig.name}`;

        // Update header
        const header = this.widget.querySelector('.bg-light');
        header.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="p-1 rounded-circle text-white ${currentModeConfig.color} me-2">
                    ${currentModeConfig.icon}
                </div>
                <div>
                    <h6 class="fw-medium text-dark mb-0 small">${currentModeConfig.name}</h6>
                    <p class="small text-muted mb-0">Ytili AI Agent</p>
                </div>
            </div>
            <div class="d-flex align-items-center">
                <button id="mode-toggle" class="btn btn-sm text-muted me-1" title="Đổi chế độ">
                    🤖
                </button>
                <button id="minimize-btn" class="btn btn-sm text-muted me-1" title="Thu gọn">
                    💬
                </button>
                <button id="close-btn" class="btn btn-sm text-muted" title="Đóng">
                    ✕
                </button>
            </div>
        `;

        // Re-attach event listeners for header buttons
        this.widget.querySelector('#mode-toggle').addEventListener('click', () => this.toggleModeSelector());
        this.widget.querySelector('#close-btn').addEventListener('click', () => this.toggleChat());
        this.widget.querySelector('#minimize-btn').addEventListener('click', () => this.toggleMinimize());
    }

    async startChatSession() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/ai-agent/chat/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(this.authToken && { 'Authorization': `Bearer ${this.authToken}` })
                },
                body: JSON.stringify({
                    conversation_type: this.currentMode,
                    context: {
                        platform: 'web',
                        timestamp: new Date().toISOString()
                    }
                })
            });

            if (!response.ok) {
                throw new Error('Failed to start chat session');
            }

            const data = await response.json();
            this.chatSession = {
                sessionId: data.session_id,
                conversationType: data.conversation_type,
                status: 'active'
            };

            // Add welcome message if provided
            if (data.welcome_message) {
                this.addMessage('assistant', data.welcome_message);
            }

        } catch (error) {
            console.error('Failed to start chat session:', error);
            this.showError('Không thể khởi tạo phiên chat');
        }
    }

    async sendMessage() {
        const messageInput = this.widget.querySelector('#message-input');
        const message = messageInput.value.trim();

        if (!message) return;

        // Add user message to UI
        this.addMessage('user', message);
        messageInput.value = '';

        // Show typing indicator
        this.showTypingIndicator();

        try {
            const response = await fetch(`${this.apiBaseUrl}/ai-agent/chat/message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(this.authToken && { 'Authorization': `Bearer ${this.authToken}` })
                },
                body: JSON.stringify({
                    session_id: this.chatSession?.sessionId,
                    message: message,
                    stream: false
                })
            });

            if (!response.ok) {
                throw new Error('Failed to send message');
            }

            const data = await response.json();

            // Hide typing indicator
            this.hideTypingIndicator();

            if (data.success) {
                // Add AI response
                this.addMessage('assistant', data.response);

                // Handle recommendations
                if (data.recommendations && data.recommendations.length > 0) {
                    this.showRecommendations(data.recommendations);
                }

                // Handle emergency detection
                if (this.currentMode === 'emergency_request' && data.emergency_data) {
                    this.handleEmergencyDetected(data.emergency_data);
                }
            } else {
                throw new Error(data.error || 'Unknown error');
            }

        } catch (error) {
            console.error('Failed to send message:', error);
            this.hideTypingIndicator();
            this.showError('Không thể gửi tin nhắn');
        }
    }

    addMessage(role, content) {
        const messagesContainer = this.widget.querySelector('#messages-container');
        const messageDiv = document.createElement('div');
        const timestamp = new Date().toLocaleTimeString('vi-VN', {
            hour: '2-digit',
            minute: '2-digit'
        });

        messageDiv.className = `d-flex align-items-start mb-3 ${role === 'user' ? 'flex-row-reverse' : ''}`;
        messageDiv.innerHTML = `
            <div class="flex-shrink-0 ${role === 'user' ? 'ms-2' : 'me-2'}">
                ${role === 'assistant' ? '🤖' : '👤'}
            </div>
            <div class="px-3 py-2 rounded ${
                role === 'user'
                    ? 'bg-primary text-white'
                    : 'bg-light text-dark'
            }" style="max-width: 250px;">
                <p class="small mb-1">${content}</p>
                <p class="small mb-0 ${role === 'user' ? 'text-white-50' : 'text-muted'}">
                    ${timestamp}
                </p>
            </div>
        `;

        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    showTypingIndicator() {
        const messagesContainer = this.widget.querySelector('#messages-container');
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typing-indicator';
        typingDiv.className = 'd-flex align-items-start mb-3';
        typingDiv.innerHTML = `
            <div class="flex-shrink-0 me-2">🤖</div>
            <div class="bg-light px-3 py-2 rounded">
                <div class="d-flex">
                    <div class="bg-secondary rounded-circle animate-bounce me-1" style="width: 8px; height: 8px;"></div>
                    <div class="bg-secondary rounded-circle animate-bounce me-1" style="width: 8px; height: 8px; animation-delay: 0.1s;"></div>
                    <div class="bg-secondary rounded-circle animate-bounce" style="width: 8px; height: 8px; animation-delay: 0.2s;"></div>
                </div>
            </div>
        `;

        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    hideTypingIndicator() {
        const typingIndicator = this.widget.querySelector('#typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    showRecommendations(recommendations) {
        this.hasNewMessage = true;
        this.widget.querySelector('#new-message-indicator').classList.remove('hidden');

        setTimeout(() => {
            this.hasNewMessage = false;
            this.widget.querySelector('#new-message-indicator').classList.add('hidden');
        }, 5000);
    }

    handleEmergencyDetected(emergencyData) {
        this.hasNewMessage = true;
        this.widget.querySelector('#new-message-indicator').classList.remove('hidden');

        // Flash the widget
        const chatToggle = this.widget.querySelector('#chat-toggle');
        chatToggle.classList.add('animate-bounce');

        setTimeout(() => {
            this.hasNewMessage = false;
            this.widget.querySelector('#new-message-indicator').classList.add('hidden');
            chatToggle.classList.remove('animate-bounce');
        }, 3000);
    }

    showError(message) {
        // Simple error display - could be enhanced
        console.error('Chat Widget Error:', message);
        this.addMessage('system', `❌ ${message}`);
    }
}

// Initialize the chat widget when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if user is authenticated
    const authToken = localStorage.getItem('ytili_auth_token') || sessionStorage.getItem('ytili_auth_token');

    // Initialize chat widget
    window.ytiliChatWidget = new YtiliChatWidget({
        apiBaseUrl: 'http://localhost:8000/api/v1',
        authToken: authToken,
        position: 'bottom-right',
        defaultMode: 'general_support'
    });
});
