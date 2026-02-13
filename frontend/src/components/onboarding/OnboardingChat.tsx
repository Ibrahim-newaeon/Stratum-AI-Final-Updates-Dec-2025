/**
 * Conversational Onboarding Chat Component
 *
 * A chat-style interface for guiding users through onboarding
 * using the RootAgent conversational flow.
 */

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChatBubbleLeftRightIcon,
  PaperAirplaneIcon,
  XMarkIcon,
  SparklesIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  quickReplies?: string[];
  progress?: number;
  requiresAction?: boolean;
  actionType?: string;
  actionData?: Record<string, unknown>;
}

interface OnboardingChatProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete?: () => void;
  initialName?: string;
  initialEmail?: string;
  language?: string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const API_BASE = (window as any).__RUNTIME_CONFIG__?.VITE_API_URL || import.meta.env.VITE_API_URL || '/api/v1';

export default function OnboardingChat({
  isOpen,
  onClose,
  onComplete,
  initialName,
  initialEmail,
  language = 'en',
}: OnboardingChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Start conversation when opened
  useEffect(() => {
    if (isOpen && !sessionId) {
      startConversation();
    }
  }, [isOpen]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen, messages]);

  const startConversation = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/onboarding-agent/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          name: initialName,
          email: initialEmail,
          language,
          is_new_tenant: false,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start conversation');
      }

      const data = await response.json();
      setSessionId(data.session_id);
      setProgress(data.progress_percent);

      setMessages([
        {
          id: '1',
          role: 'assistant',
          content: data.message,
          timestamp: new Date(),
          quickReplies: data.quick_replies,
          progress: data.progress_percent,
        },
      ]);
    } catch (err) {
      setError('Failed to start onboarding. Please try again.');
      console.error('Start conversation error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = async (message: string) => {
    if (!message.trim() || !sessionId || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/onboarding-agent/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          session_id: sessionId,
          message,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const data = await response.json();
      setProgress(data.progress_percent);

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.message,
        timestamp: new Date(),
        quickReplies: data.quick_replies,
        progress: data.progress_percent,
        requiresAction: data.requires_action,
        actionType: data.action_type,
        actionData: data.action_data,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Handle special actions
      if (data.action_type === 'redirect' && data.action_data?.url) {
        // Onboarding complete - redirect to dashboard
        setTimeout(() => {
          onComplete?.();
          window.location.href = data.action_data.url;
        }, 2000);
      } else if (data.action_type === 'oauth_redirect' && data.action_data?.platform) {
        // Handle OAuth flow
        handleOAuthRedirect(data.action_data.platform);
      }
    } catch (err) {
      setError('Failed to send message. Please try again.');
      console.error('Send message error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOAuthRedirect = (platform: string) => {
    // Open OAuth popup or redirect
    const oauthUrl = `${API_BASE}/oauth/${platform}/authorize`;
    window.open(oauthUrl, '_blank', 'width=600,height=700');
  };

  const handleQuickReply = (reply: string) => {
    sendMessage(reply);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputValue);
    }
  };

  const resetConversation = () => {
    setMessages([]);
    setSessionId(null);
    setProgress(0);
    startConversation();
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="fixed bottom-4 right-4 w-[400px] h-[600px] bg-[#0b1215] border border-[#00c7be]/20 rounded-2xl shadow-2xl flex flex-col overflow-hidden z-50"
        style={{ boxShadow: '0 0 40px rgba(0, 199, 190, 0.15)' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#00c7be]/20 bg-gradient-to-r from-[#00c7be]/10 to-[#00c7be]/5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#00c7be] flex items-center justify-center shadow-lg" style={{ boxShadow: '0 0 20px rgba(0, 199, 190, 0.4)' }}>
              <SparklesIcon className="w-5 h-5 text-[#0b1215]" />
            </div>
            <div>
              <h3 className="font-semibold text-white">Stratum AI Assistant</h3>
              <p className="text-xs text-[#00c7be]">Trust-Gated Onboarding</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={resetConversation}
              className="p-2 rounded-lg hover:bg-[#00c7be]/10 text-gray-400 hover:text-[#00c7be] transition-colors"
              title="Start Over"
            >
              <ArrowPathIcon className="w-5 h-5" />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-[#00c7be]/10 text-gray-400 hover:text-white transition-colors"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="h-1 bg-[rgba(255,_255,_255,_0.05)]">
          <motion.div
            className="h-full bg-gradient-to-r from-[#00c7be] to-[#F4D03F]"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn('flex', message.role === 'user' ? 'justify-end' : 'justify-start')}
            >
              <div
                className={cn(
                  'max-w-[85%] rounded-2xl px-4 py-3',
                  message.role === 'user'
                    ? 'bg-[#00c7be] text-[#0b1215] font-medium'
                    : 'bg-[rgba(255, 255, 255, 0.05)] border border-[#00c7be]/10 text-gray-200'
                )}
              >
                {/* Message content with markdown-like formatting */}
                <div className="text-sm whitespace-pre-wrap">
                  {message.content.split('\n').map((line, i) => {
                    // Bold text
                    const formattedLine = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                    return (
                      <p
                        key={i}
                        className={i > 0 ? 'mt-2' : ''}
                        dangerouslySetInnerHTML={{ __html: formattedLine }}
                      />
                    );
                  })}
                </div>

                {/* Quick Replies */}
                {message.role === 'assistant' &&
                  message.quickReplies &&
                  message.quickReplies.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-[#00c7be]/10">
                      {message.quickReplies.map((reply, index) => (
                        <button
                          key={index}
                          onClick={() => handleQuickReply(reply)}
                          disabled={isLoading}
                          className="px-3 py-1.5 text-xs font-medium bg-[#00c7be]/10 hover:bg-[#00c7be]/20 border border-[#00c7be]/20 rounded-full text-[#00c7be] hover:text-[#f0c95c] transition-colors disabled:opacity-50"
                        >
                          {reply}
                        </button>
                      ))}
                    </div>
                  )}

                {/* Action Button */}
                {message.requiresAction && message.actionType === 'oauth_redirect' && (
                  <button
                    onClick={() => handleOAuthRedirect(message.actionData?.platform as string)}
                    className="mt-3 w-full py-2 px-4 bg-[#00c7be] hover:bg-[#f0c95c] text-[#0b1215] text-sm font-semibold rounded-lg transition-all hover:shadow-lg"
                    style={{ boxShadow: '0 0 20px rgba(0, 199, 190, 0.3)' }}
                  >
                    Connect {String(message.actionData?.platform)}
                  </button>
                )}
              </div>
            </motion.div>
          ))}

          {/* Loading Indicator */}
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="bg-[rgba(255,_255,_255,_0.05)] border border-[#00c7be]/10 rounded-2xl px-4 py-3">
                <div className="flex gap-1">
                  <span
                    className="w-2 h-2 bg-[#00c7be] rounded-full animate-bounce"
                    style={{ animationDelay: '0ms' }}
                  />
                  <span
                    className="w-2 h-2 bg-[#00c7be] rounded-full animate-bounce"
                    style={{ animationDelay: '150ms' }}
                  />
                  <span
                    className="w-2 h-2 bg-[#00c7be] rounded-full animate-bounce"
                    style={{ animationDelay: '300ms' }}
                  />
                </div>
              </div>
            </motion.div>
          )}

          {/* Error Message */}
          {error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-center"
            >
              <div className="flex items-center gap-2 px-4 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                <ExclamationTriangleIcon className="w-4 h-4" />
                {error}
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Progress Indicator */}
        {progress > 0 && progress < 100 && (
          <div className="px-4 py-2 border-t border-[#00c7be]/10 bg-[rgba(255,_255,_255,_0.025)]">
            <div className="flex items-center justify-between text-xs text-gray-400">
              <span>Setup Progress</span>
              <span className="text-[#00c7be] font-semibold">{progress}%</span>
            </div>
          </div>
        )}

        {/* Completed State */}
        {progress === 100 && (
          <div className="px-4 py-3 border-t border-[#00c7be]/20 bg-[#00c7be]/10">
            <div className="flex items-center gap-2 text-[#00c7be] text-sm font-medium">
              <CheckCircleIcon className="w-5 h-5" />
              <span>Onboarding Complete!</span>
            </div>
          </div>
        )}

        {/* Input */}
        <div className="p-4 border-t border-[#00c7be]/20 bg-[#0b1215]">
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              disabled={isLoading || progress === 100}
              className="flex-1 bg-[rgba(255,_255,_255,_0.05)] border border-[#00c7be]/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-[#00c7be]/50 disabled:opacity-50 transition-colors"
            />
            <button
              onClick={() => sendMessage(inputValue)}
              disabled={!inputValue.trim() || isLoading || progress === 100}
              className="p-3 bg-[#00c7be] hover:bg-[#f0c95c] rounded-xl text-[#0b1215] transition-all disabled:opacity-50 disabled:hover:bg-[#00c7be]"
              style={{ boxShadow: '0 0 15px rgba(0, 199, 190, 0.3)' }}
            >
              <PaperAirplaneIcon className="w-5 h-5" />
            </button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

/**
 * Floating button to trigger onboarding chat
 */
export function OnboardingChatButton({
  onClick,
  pulse = false,
}: {
  onClick: () => void;
  pulse?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'fixed bottom-4 right-4 w-14 h-14 rounded-full text-white shadow-lg hover:shadow-xl transition-all z-40 flex items-center justify-center',
        pulse && 'animate-pulse'
      )}
      style={{
        background: 'linear-gradient(135deg, #8B5CF6 0%, #3B82F6 100%)',
        boxShadow: '0 0 30px rgba(139, 92, 246, 0.4)'
      }}
    >
      <SparklesIcon className="w-6 h-6" />
    </button>
  );
}
