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

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

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
        className="fixed bottom-4 right-4 w-[400px] h-[600px] bg-[#0a0a0f] border border-white/10 rounded-2xl shadow-2xl flex flex-col overflow-hidden z-50"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/10 bg-gradient-to-r from-cyan-500/10 to-purple-500/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-purple-500 flex items-center justify-center">
              <SparklesIcon className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-white">Stratum AI Assistant</h3>
              <p className="text-xs text-gray-400">Onboarding Guide</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={resetConversation}
              className="p-2 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-colors"
              title="Start Over"
            >
              <ArrowPathIcon className="w-5 h-5" />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-colors"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="h-1 bg-gray-800">
          <motion.div
            className="h-full bg-gradient-to-r from-cyan-500 to-purple-500"
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
                    ? 'bg-gradient-to-r from-cyan-500 to-purple-500 text-white'
                    : 'bg-[#12121a] border border-white/5 text-gray-200'
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
                    <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-white/10">
                      {message.quickReplies.map((reply, index) => (
                        <button
                          key={index}
                          onClick={() => handleQuickReply(reply)}
                          disabled={isLoading}
                          className="px-3 py-1.5 text-xs font-medium bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-gray-300 hover:text-white transition-colors disabled:opacity-50"
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
                    className="mt-3 w-full py-2 px-4 bg-gradient-to-r from-cyan-500 to-purple-500 text-white text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
                  >
                    Connect {message.actionData?.platform}
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
              <div className="bg-[#12121a] border border-white/5 rounded-2xl px-4 py-3">
                <div className="flex gap-1">
                  <span
                    className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
                    style={{ animationDelay: '0ms' }}
                  />
                  <span
                    className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
                    style={{ animationDelay: '150ms' }}
                  />
                  <span
                    className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
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
          <div className="px-4 py-2 border-t border-white/5 bg-[#12121a]/50">
            <div className="flex items-center justify-between text-xs text-gray-400">
              <span>Setup Progress</span>
              <span className="text-cyan-400">{progress}%</span>
            </div>
          </div>
        )}

        {/* Completed State */}
        {progress === 100 && (
          <div className="px-4 py-3 border-t border-white/5 bg-green-500/10">
            <div className="flex items-center gap-2 text-green-400 text-sm">
              <CheckCircleIcon className="w-5 h-5" />
              <span>Onboarding Complete!</span>
            </div>
          </div>
        )}

        {/* Input */}
        <div className="p-4 border-t border-white/10 bg-[#0a0a0f]">
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              disabled={isLoading || progress === 100}
              className="flex-1 bg-[#12121a] border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500/50 disabled:opacity-50"
            />
            <button
              onClick={() => sendMessage(inputValue)}
              disabled={!inputValue.trim() || isLoading || progress === 100}
              className="p-3 bg-gradient-to-r from-cyan-500 to-purple-500 rounded-xl text-white hover:opacity-90 transition-opacity disabled:opacity-50"
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
        'fixed bottom-4 right-4 w-14 h-14 rounded-full bg-gradient-to-r from-cyan-500 to-purple-500 text-white shadow-lg hover:shadow-xl transition-all z-40 flex items-center justify-center',
        pulse && 'animate-pulse'
      )}
    >
      <ChatBubbleLeftRightIcon className="w-6 h-6" />
    </button>
  );
}
