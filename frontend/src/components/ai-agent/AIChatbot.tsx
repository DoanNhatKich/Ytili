/**
 * AI Chatbot Component for Ytili Platform
 * Real-time chat interface with streaming responses and voice capabilities
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Mic, MicOff, Bot, User, AlertCircle, CheckCircle } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

interface ChatSession {
  sessionId: string;
  conversationType: string;
  status: 'active' | 'completed';
}

interface Recommendation {
  type: string;
  title: string;
  description: string;
  data: any;
  confidence: number;
}

interface AIChatbotProps {
  apiBaseUrl?: string;
  authToken?: string;
  conversationType?: 'donation_advisory' | 'medical_info' | 'campaign_help' | 'emergency_request' | 'general_support';
  onRecommendation?: (recommendation: Recommendation) => void;
  onEmergencyDetected?: (emergencyData: any) => void;
  className?: string;
}

export const AIChatbot: React.FC<AIChatbotProps> = ({
  apiBaseUrl = '/api/v1',
  authToken,
  conversationType = 'general_support',
  onRecommendation,
  onEmergencyDetected,
  className = ''
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [chatSession, setChatSession] = useState<ChatSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  
  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);
  
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);
  
  // Initialize speech recognition
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'vi-VN'; // Vietnamese
      
      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInputMessage(transcript);
        setIsListening(false);
      };
      
      recognitionRef.current.onerror = () => {
        setIsListening(false);
        setError('Lỗi nhận dạng giọng nói');
      };
      
      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }
  }, []);
  
  // Start chat session
  const startChatSession = useCallback(async (initialMessage?: string) => {
    try {
      const response = await fetch(`${apiBaseUrl}/ai-agent/chat/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authToken && { 'Authorization': `Bearer ${authToken}` })
        },
        body: JSON.stringify({
          conversation_type: conversationType,
          initial_message: initialMessage,
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
      
      setChatSession({
        sessionId: data.session_id,
        conversationType: data.conversation_type,
        status: 'active'
      });
      
      // Add welcome message if provided
      if (data.welcome_message) {
        const welcomeMessage: Message = {
          id: `welcome-${Date.now()}`,
          role: 'assistant',
          content: data.welcome_message,
          timestamp: new Date()
        };
        setMessages([welcomeMessage]);
      }
      
      return data.session_id;
    } catch (err) {
      setError('Không thể khởi tạo phiên chat');
      console.error('Failed to start chat session:', err);
      return null;
    }
  }, [apiBaseUrl, authToken, conversationType]);
  
  // Send message
  const sendMessage = useCallback(async (message: string, sessionId?: string) => {
    if (!message.trim()) return;
    
    const currentSessionId = sessionId || chatSession?.sessionId;
    if (!currentSessionId) {
      const newSessionId = await startChatSession(message);
      if (!newSessionId) return;
      return; // The initial message will be processed by startChatSession
    }
    
    // Add user message
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${apiBaseUrl}/ai-agent/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authToken && { 'Authorization': `Bearer ${authToken}` })
        },
        body: JSON.stringify({
          session_id: currentSessionId,
          message: message,
          stream: false // For now, using non-streaming
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to send message');
      }
      
      const data = await response.json();
      
      if (data.success) {
        // Add AI response
        const aiMessage: Message = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: data.response,
          timestamp: new Date()
        };
        
        setMessages(prev => [...prev, aiMessage]);
        
        // Handle recommendations
        if (data.recommendations && data.recommendations.length > 0) {
          setRecommendations(data.recommendations);
          data.recommendations.forEach((rec: Recommendation) => {
            onRecommendation?.(rec);
          });
        }
        
        // Handle emergency detection
        if (conversationType === 'emergency_request' && data.emergency_data) {
          onEmergencyDetected?.(data.emergency_data);
        }
      } else {
        throw new Error(data.error || 'Unknown error');
      }
    } catch (err) {
      setError('Không thể gửi tin nhắn');
      console.error('Failed to send message:', err);
    } finally {
      setIsLoading(false);
    }
  }, [chatSession, apiBaseUrl, authToken, conversationType, onRecommendation, onEmergencyDetected, startChatSession]);
  
  // Handle form submission
  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (inputMessage.trim() && !isLoading) {
      sendMessage(inputMessage);
    }
  }, [inputMessage, isLoading, sendMessage]);
  
  // Handle voice input
  const toggleVoiceInput = useCallback(() => {
    if (!recognitionRef.current) {
      setError('Trình duyệt không hỗ trợ nhận dạng giọng nói');
      return;
    }
    
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.start();
      setIsListening(true);
      setError(null);
    }
  }, [isListening]);
  
  // Initialize chat session on mount
  useEffect(() => {
    if (!chatSession) {
      startChatSession();
    }
  }, [chatSession, startChatSession]);
  
  const getMessageIcon = (role: string) => {
    switch (role) {
      case 'assistant':
        return <Bot className="w-6 h-6 text-blue-600" />;
      case 'user':
        return <User className="w-6 h-6 text-gray-600" />;
      default:
        return null;
    }
  };
  
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('vi-VN', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };
  
  return (
    <div className={`flex flex-col h-full bg-white border border-gray-200 rounded-lg shadow-lg ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-blue-50">
        <div className="flex items-center space-x-2">
          <Bot className="w-6 h-6 text-blue-600" />
          <div>
            <h3 className="font-semibold text-gray-900">Ytili AI Agent</h3>
            <p className="text-sm text-gray-600">
              {conversationType === 'donation_advisory' && 'Tư vấn quyên góp'}
              {conversationType === 'medical_info' && 'Thông tin y tế'}
              {conversationType === 'campaign_help' && 'Hỗ trợ chiến dịch'}
              {conversationType === 'emergency_request' && 'Yêu cầu khẩn cấp'}
              {conversationType === 'general_support' && 'Hỗ trợ chung'}
            </p>
          </div>
        </div>
        {chatSession && (
          <div className="flex items-center space-x-1">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span className="text-sm text-green-600">Đã kết nối</span>
          </div>
        )}
      </div>
      
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex items-start space-x-3 ${
              message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
            }`}
          >
            <div className="flex-shrink-0">
              {getMessageIcon(message.role)}
            </div>
            <div
              className={`flex-1 max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white ml-auto'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              <p className={`text-xs mt-1 ${
                message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
              }`}>
                {formatTime(message.timestamp)}
              </p>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex items-start space-x-3">
            <Bot className="w-6 h-6 text-blue-600" />
            <div className="bg-gray-100 px-4 py-2 rounded-lg">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="border-t border-gray-200 p-4 bg-yellow-50">
          <h4 className="font-semibold text-sm text-gray-900 mb-2">Gợi ý từ AI:</h4>
          <div className="space-y-2">
            {recommendations.map((rec, index) => (
              <div key={index} className="bg-white p-3 rounded border border-yellow-200">
                <h5 className="font-medium text-sm text-gray-900">{rec.title}</h5>
                <p className="text-xs text-gray-600 mt-1">{rec.description}</p>
                <div className="flex justify-between items-center mt-2">
                  <span className="text-xs text-gray-500">
                    Độ tin cậy: {Math.round(rec.confidence * 100)}%
                  </span>
                  <button className="text-xs text-blue-600 hover:text-blue-800">
                    Xem chi tiết
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Error message */}
      {error && (
        <div className="border-t border-gray-200 p-4 bg-red-50">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-red-500" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </div>
      )}
      
      {/* Input */}
      <div className="border-t border-gray-200 p-4">
        <form onSubmit={handleSubmit} className="flex items-center space-x-2">
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Nhập tin nhắn của bạn..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isLoading}
            />
          </div>
          
          {recognitionRef.current && (
            <button
              type="button"
              onClick={toggleVoiceInput}
              className={`p-2 rounded-lg transition-colors ${
                isListening
                  ? 'bg-red-100 text-red-600 hover:bg-red-200'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
              disabled={isLoading}
            >
              {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>
          )}
          
          <button
            type="submit"
            disabled={!inputMessage.trim() || isLoading}
            className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
};

export default AIChatbot;
