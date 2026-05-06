import { useState, useRef, useEffect, useCallback } from 'react';
import {
  MessageSquare,
  Send,
  X,
  Sparkles,
  Loader2,
  TrendingUp,
  TrendingDown,
  ChevronRight,
  Bot,
  User,
  Minimize2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useCopilotChat } from '@/api/copilot';
import type { CopilotMessage, CopilotDataCard } from '@/api/copilot';

function DataCard({ card }: { card: CopilotDataCard }) {
  const statusColors: Record<string, string> = {
    healthy: 'text-emerald-600',
    degraded: 'text-amber-600',
    critical: 'text-red-600',
    low: 'text-emerald-600',
    moderate: 'text-blue-600',
    elevated: 'text-amber-600',
    high: 'text-red-600',
  };
  const valueColor = card.status
    ? statusColors[card.status] || 'text-foreground'
    : 'text-foreground';

  return (
    <div className="flex items-center justify-between bg-muted/30 rounded-lg px-3 py-2 border border-border/50">
      <span className="text-[11px] text-muted-foreground font-medium">{card.label}</span>
      <div className="flex items-center gap-1.5">
        <span className={cn('text-sm font-bold', valueColor)}>{card.value}</span>
        {card.change != null && (
          <span
            className={cn(
              'text-[10px] font-semibold flex items-center',
              card.change >= 0 ? 'text-emerald-600' : 'text-red-500'
            )}
          >
            {card.change >= 0 ? (
              <TrendingUp className="w-3 h-3 mr-0.5" />
            ) : (
              <TrendingDown className="w-3 h-3 mr-0.5" />
            )}
            {Math.abs(card.change).toFixed(1)}%
          </span>
        )}
      </div>
    </div>
  );
}

function MessageBubble({ msg }: { msg: CopilotMessage }) {
  const isUser = msg.role === 'user';

  // Simple markdown-like rendering (bold only)
  const formatContent = (text: string) => {
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} className="font-bold">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <div className={cn('flex gap-2.5 max-w-[95%]', isUser ? 'ml-auto flex-row-reverse' : '')}>
      <div
        className={cn(
          'w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5',
          isUser ? 'bg-primary/10' : 'bg-primary'
        )}
      >
        {isUser ? (
          <User className="w-3.5 h-3.5 text-primary" />
        ) : (
          <Bot className="w-3.5 h-3.5 text-white" />
        )}
      </div>
      <div
        className={cn(
          'rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
          isUser
            ? 'bg-primary text-primary-foreground rounded-tr-md'
            : 'bg-muted/50 border border-border/50 text-foreground rounded-tl-md'
        )}
      >
        <div className="whitespace-pre-wrap">{formatContent(msg.content)}</div>

        {/* Data Cards */}
        {msg.data_cards && msg.data_cards.length > 0 && (
          <div className="mt-2.5 space-y-1.5">
            {msg.data_cards.map((card, i) => (
              <DataCard key={i} card={card} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SuggestionChip({ text, onClick }: { text: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-primary bg-primary/5 hover:bg-primary/10 border border-primary/20 rounded-full transition-colors whitespace-nowrap"
    >
      <ChevronRight className="w-3 h-3" />
      {text}
    </button>
  );
}

export function CopilotChat() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | undefined>();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const chatMutation = useCopilotChat();

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  // Welcome message on first open
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content:
            "Hi! I'm your Stratum AI Copilot. I can help you understand your campaigns, signal health, anomalies, and more. What would you like to know?",
          timestamp: new Date().toISOString(),
          suggestions: [
            'How are my campaigns doing?',
            'Any anomalies today?',
            "What's my signal health?",
            'Help',
          ],
        },
      ]);
    }
  }, [isOpen, messages.length]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || chatMutation.isPending) return;

    const userMsg: CopilotMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');

    try {
      const response = await chatMutation.mutateAsync({
        message: text.trim(),
        session_id: sessionId,
      });

      setSessionId(response.session_id);

      const assistantMsg: CopilotMessage = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content: response.message,
        timestamp: response.timestamp,
        suggestions: response.suggestions,
        data_cards: response.data_cards,
        intent: response.intent,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: CopilotMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: "Sorry, I couldn't process that request. Please try again.",
        timestamp: new Date().toISOString(),
        suggestions: ['How are my campaigns doing?', 'Help'],
      };
      setMessages((prev) => [...prev, errorMsg]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleSuggestion = (text: string) => {
    sendMessage(text);
  };

  // Get last assistant message's suggestions
  const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant');
  const suggestions = lastAssistant?.suggestions || [];

  return (
    <>
      {/* Floating Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-20 right-4 z-50 w-14 h-14 rounded-full bg-primary text-primary-foreground shadow-lg hover:shadow-xl hover:scale-105 transition-transform transition-colors flex items-center justify-center group"
          aria-label="Open AI Copilot"
        >
          <Sparkles className="w-6 h-6 group-hover:rotate-12 transition-transform" />
          <span className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-400 rounded-full border-2 border-white" />
        </button>
      )}

      {/* Chat Panel */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-50 w-[400px] h-[600px] max-h-[80vh] max-w-[calc(100vw-3rem)] rounded-2xl border bg-card shadow-2xl flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b bg-primary text-primary-foreground">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-foreground/20 flex items-center justify-center">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold tracking-tight">AI Copilot</h3>
                <p className="text-[10px] text-foreground/70 font-medium">Stratum Intelligence</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 rounded-lg hover:bg-foreground/20 transition-colors"
                aria-label="Minimize"
              >
                <Minimize2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => {
                  setIsOpen(false);
                  setMessages([]);
                  setSessionId(undefined);
                }}
                className="p-1.5 rounded-lg hover:bg-foreground/20 transition-colors"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}

            {/* Loading indicator */}
            {chatMutation.isPending && (
              <div className="flex gap-2.5">
                <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                  <Bot className="w-3.5 h-3.5 text-white" />
                </div>
                <div className="bg-muted/50 border border-border/50 rounded-2xl rounded-tl-md px-4 py-3">
                  <div className="flex items-center gap-1.5">
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-violet-500" />
                    <span className="text-xs text-muted-foreground">Analyzing your data...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Suggestions */}
          {suggestions.length > 0 && !chatMutation.isPending && (
            <div className="px-4 pb-2 flex flex-wrap gap-1.5">
              {suggestions.map((s, i) => (
                <SuggestionChip key={i} text={s} onClick={() => handleSuggestion(s)} />
              ))}
            </div>
          )}

          {/* Input */}
          <form onSubmit={handleSubmit} className="px-4 py-3 border-t bg-card">
            <div className="flex items-center gap-2 bg-muted/30 rounded-xl border border-border/50 px-3 py-1.5 focus-within:border-violet-400 focus-within:ring-1 focus-within:ring-violet-400/30 transition-colors">
              <MessageSquare className="w-4 h-4 text-muted-foreground flex-shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about your campaigns..."
                aria-label="Ask about your campaigns"
                className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/60 outline-none py-1.5"
                disabled={chatMutation.isPending}
              />
              <button
                type="submit"
                disabled={!input.trim() || chatMutation.isPending}
                aria-label="Send message"
                className={cn(
                  'p-1.5 rounded-lg transition-colors',
                  input.trim() ? 'text-violet-600 hover:bg-violet-100' : 'text-muted-foreground/40'
                )}
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
