/**
 * Floating Chat Widget Component for Ytili Platform
 * Provides a floating AI chat interface with multiple conversation modes
 */
import React, { useState, useEffect, useRef } from 'react';
import { MessageCircle, X, AlertTriangle, Heart, HelpCircle, Phone, Bot } from 'lucide-react';
import { AIChatbot } from './AIChatbot';

export interface ChatWidgetProps {
  apiBaseUrl?: string;
  authToken?: string;
  className?: string;
  position?: 'bottom-right' | 'bottom-left' | 'bottom-center';
  defaultMode?: 'donation_advisory' | 'medical_info' | 'campaign_help' | 'emergency_request' | 'general_support';
}

interface ConversationMode {
  id: string;
  name: string;
  icon: React.ReactNode;
  color: string;
  description: string;
  disclaimer?: string;
}

export const ChatWidget: React.FC<ChatWidgetProps> = ({
  apiBaseUrl = '/api/v1',
  authToken,
  className = '',
  position = 'bottom-right',
  defaultMode = 'general_support'
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [currentMode, setCurrentMode] = useState(defaultMode);
  const [showModeSelector, setShowModeSelector] = useState(false);
  const [hasNewMessage, setHasNewMessage] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  
  const widgetRef = useRef<HTMLDivElement>(null);
  
  // Conversation modes configuration
  const conversationModes: ConversationMode[] = [
    {
      id: 'donation_advisory',
      name: 'Tư vấn quyên góp',
      icon: <Heart className="w-4 h-4" />,
      color: 'bg-blue-600',
      description: 'Nhận gợi ý quyên góp thông minh dựa trên nhu cầu thực tế'
    },
    {
      id: 'medical_info',
      name: 'Thông tin y tế',
      icon: <Bot className="w-4 h-4" />,
      color: 'bg-green-600',
      description: 'Thông tin y tế cơ bản và hướng dẫn sức khỏe',
      disclaimer: 'Thông tin chỉ mang tính tham khảo, không thay thế ý kiến bác sĩ'
    },
    {
      id: 'campaign_help',
      name: 'Hỗ trợ chiến dịch',
      icon: <HelpCircle className="w-4 h-4" />,
      color: 'bg-purple-600',
      description: 'Hỗ trợ tạo và quản lý chiến dịch quyên góp'
    },
    {
      id: 'emergency_request',
      name: 'Yêu cầu khẩn cấp',
      icon: <AlertTriangle className="w-4 h-4" />,
      color: 'bg-red-600',
      description: 'Hỗ trợ khẩn cấp cho các tình huống y tế cấp bách'
    },
    {
      id: 'general_support',
      name: 'Hỗ trợ chung',
      icon: <MessageCircle className="w-4 h-4" />,
      color: 'bg-gray-600',
      description: 'Hỗ trợ chung về nền tảng và các tính năng'
    }
  ];
  
  const currentModeConfig = conversationModes.find(mode => mode.id === currentMode) || conversationModes[4];
  
  // Position classes
  const getPositionClasses = () => {
    switch (position) {
      case 'bottom-left':
        return 'bottom-4 left-4';
      case 'bottom-center':
        return 'bottom-4 left-1/2 transform -translate-x-1/2';
      case 'bottom-right':
      default:
        return 'bottom-4 right-4';
    }
  };
  
  // Handle click outside to close mode selector
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (widgetRef.current && !widgetRef.current.contains(event.target as Node)) {
        setShowModeSelector(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);
  
  // Handle emergency mode
  const handleEmergencyDetected = (emergencyData: any) => {
    // Flash the widget to indicate emergency
    setHasNewMessage(true);
    setTimeout(() => setHasNewMessage(false), 3000);
    
    // Could trigger additional emergency protocols here
    console.log('Emergency detected:', emergencyData);
  };
  
  // Handle recommendations
  const handleRecommendation = (recommendation: any) => {
    setHasNewMessage(true);
    setTimeout(() => setHasNewMessage(false), 5000);
  };
  
  // Toggle chat widget
  const toggleChat = () => {
    setIsOpen(!isOpen);
    setShowModeSelector(false);
    if (!isOpen) {
      setIsMinimized(false);
    }
  };
  
  // Change conversation mode
  const changeMode = (modeId: string) => {
    setCurrentMode(modeId);
    setShowModeSelector(false);
    if (!isOpen) {
      setIsOpen(true);
    }
  };
  
  // Emergency SOS button
  const handleEmergencyClick = () => {
    setCurrentMode('emergency_request');
    setIsOpen(true);
    setShowModeSelector(false);
  };
  
  return (
    <div ref={widgetRef} className={`fixed z-50 ${getPositionClasses()} ${className}`}>
      {/* Mode Selector Popup */}
      {showModeSelector && (
        <div className="absolute bottom-16 right-0 mb-2 w-80 bg-white rounded-lg shadow-xl border border-gray-200 p-4">
          <h3 className="font-semibold text-gray-900 mb-3">Chọn loại hỗ trợ</h3>
          <div className="space-y-2">
            {conversationModes.map((mode) => (
              <button
                key={mode.id}
                onClick={() => changeMode(mode.id)}
                className={`w-full text-left p-3 rounded-lg border transition-colors hover:bg-gray-50 ${
                  currentMode === mode.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-full text-white ${mode.color}`}>
                    {mode.icon}
                  </div>
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900">{mode.name}</h4>
                    <p className="text-sm text-gray-600">{mode.description}</p>
                    {mode.disclaimer && (
                      <p className="text-xs text-orange-600 mt-1">⚠️ {mode.disclaimer}</p>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
      
      {/* Emergency SOS Button */}
      <div className="absolute -top-16 right-0">
        <button
          onClick={handleEmergencyClick}
          className="bg-red-600 hover:bg-red-700 text-white p-3 rounded-full shadow-lg transition-all duration-200 animate-pulse"
          title="Yêu cầu khẩn cấp"
        >
          <Phone className="w-5 h-5" />
        </button>
      </div>
      
      {/* Chat Window */}
      {isOpen && (
        <div className={`absolute bottom-16 right-0 w-96 h-96 bg-white rounded-lg shadow-xl border border-gray-200 flex flex-col ${
          isMinimized ? 'h-12' : 'h-96'
        } transition-all duration-300`}>
          {/* Header */}
          <div className="flex items-center justify-between p-3 border-b border-gray-200 bg-gray-50 rounded-t-lg">
            <div className="flex items-center space-x-2">
              <div className={`p-1 rounded-full text-white ${currentModeConfig.color}`}>
                {currentModeConfig.icon}
              </div>
              <div>
                <h3 className="font-medium text-gray-900 text-sm">{currentModeConfig.name}</h3>
                <p className="text-xs text-gray-600">Ytili AI Agent</p>
              </div>
            </div>
            <div className="flex items-center space-x-1">
              <button
                onClick={() => setShowModeSelector(!showModeSelector)}
                className="p-1 text-gray-500 hover:text-gray-700 rounded"
                title="Đổi chế độ"
              >
                <Bot className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsMinimized(!isMinimized)}
                className="p-1 text-gray-500 hover:text-gray-700 rounded"
                title={isMinimized ? 'Mở rộng' : 'Thu gọn'}
              >
                <MessageCircle className="w-4 h-4" />
              </button>
              <button
                onClick={toggleChat}
                className="p-1 text-gray-500 hover:text-gray-700 rounded"
                title="Đóng"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          {/* Chat Content */}
          {!isMinimized && (
            <div className="flex-1 overflow-hidden">
              <AIChatbot
                apiBaseUrl={apiBaseUrl}
                authToken={authToken}
                conversationType={currentMode as any}
                onRecommendation={handleRecommendation}
                onEmergencyDetected={handleEmergencyDetected}
                className="h-full border-0 shadow-none rounded-none"
              />
            </div>
          )}
        </div>
      )}
      
      {/* Floating Button */}
      <button
        onClick={toggleChat}
        className={`relative p-4 rounded-full shadow-lg transition-all duration-200 text-white ${
          currentModeConfig.color
        } hover:scale-110 ${hasNewMessage ? 'animate-bounce' : ''}`}
        title={`Ytili AI Agent - ${currentModeConfig.name}`}
      >
        {currentModeConfig.icon}
        
        {/* New message indicator */}
        {hasNewMessage && (
          <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-ping"></div>
        )}
        
        {/* Mode indicator */}
        <div className="absolute -top-2 -left-2 w-4 h-4 bg-white rounded-full flex items-center justify-center">
          <div className={`w-2 h-2 rounded-full ${currentModeConfig.color}`}></div>
        </div>
      </button>
      
      {/* Mobile responsive adjustments */}
      <style jsx>{`
        @media (max-width: 768px) {
          .w-96 {
            width: calc(100vw - 2rem);
            max-width: 24rem;
          }
          .h-96 {
            height: 70vh;
            max-height: 24rem;
          }
        }
      `}</style>
    </div>
  );
};

export default ChatWidget;
