/**
 * TeamChat — Integrated team chat panel for real-time communication.
 *
 * Features:
 * - Send/receive messages in real-time
 * - Reply to messages
 * - @mention users
 * - Search messages
 * - Unread message counter badge
 *
 * Feature 3.1 — Mode multi-utilisateurs en temps réel.
 */

import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { MessageCircle, Send, X, Search, Reply, ChevronDown } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useCollaborationStore, type ChatMessage } from '../../stores/collaboration-store';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function _formatDateSeparator(iso: string, t: (key: string) => string): string {
  try {
    const d = new Date(iso);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (d.toDateString() === today.toDateString()) return t('chat.today');
    if (d.toDateString() === yesterday.toDateString()) return t('chat.yesterday');
    return d.toLocaleDateString();
  } catch {
    return '';
  }
}

interface MessageBubbleProps {
  message: ChatMessage;
  isOwn: boolean;
  onReply: (message: ChatMessage) => void;
}

function MessageBubble({ message, isOwn, onReply }: MessageBubbleProps) {
  const users = useCollaborationStore((s) => s.users);
  const senderColor = users.find((u) => u.userId === message.senderId)?.avatarColor ?? '#6366f1';

  return (
    <div className={cn('group flex gap-2', isOwn ? 'flex-row-reverse' : 'flex-row')}>
      <div
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold text-white"
        style={{ backgroundColor: senderColor }}
      >
        {message.senderName.slice(0, 2).toUpperCase()}
      </div>
      <div className={cn('max-w-[75%] space-y-0.5', isOwn ? 'items-end' : 'items-start')}>
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-foreground">{message.senderName}</span>
          <span className="text-[10px] text-muted-foreground">{formatTime(message.timestamp)}</span>
        </div>
        <div
          className={cn(
            'rounded-lg px-3 py-1.5 text-sm',
            isOwn
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-foreground'
          )}
        >
          {message.content}
        </div>
        <button type="button"
          onClick={() => onReply(message)}
          className="hidden text-xs text-muted-foreground hover:text-foreground group-hover:inline-flex items-center gap-0.5"
        >
          <Reply className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}

export function TeamChat() {
  const { t } = useTranslation('collaboration');
  const chatOpen = useCollaborationStore((s) => s.chatOpen);
  const toggleChat = useCollaborationStore((s) => s.toggleChat);
  const chatMessages = useCollaborationStore((s) => s.chatMessages);
  const sendMessage = useCollaborationStore((s) => s.sendMessage);
  const currentUserId = useCollaborationStore((s) => s.currentUserId);
  const unreadCount = useCollaborationStore((s) => s.unreadChatCount);
  const chatEnabled = useCollaborationStore((s) => s.settings.chatEnabled);
  const replyingTo = useCollaborationStore((s) => s.replyingTo);
  const setReplyingTo = useCollaborationStore((s) => s.setReplyingTo);

  const [inputValue, setInputValue] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    if (chatOpen) inputRef.current?.focus();
  }, [chatOpen]);

  if (!chatEnabled) return null;

  const filteredMessages = searchQuery
    ? chatMessages.filter((m) => m.content.toLowerCase().includes(searchQuery.toLowerCase()))
    : chatMessages;

  const handleSend = () => {
    if (!inputValue.trim()) return;
    sendMessage(inputValue);
    setInputValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Floating toggle button
  if (!chatOpen) {
    return (
      <button type="button"
        onClick={toggleChat}
        className="fixed bottom-4 right-4 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg hover:bg-primary/90 transition-colors"
        aria-label={t('chat.title')}
      >
        <MessageCircle className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex w-80 flex-col rounded-xl border bg-background shadow-2xl" style={{ height: '28rem' }}>
      {/* Header */}
      <div className="flex items-center justify-between border-b px-3 py-2">
        <h3 className="text-sm font-semibold">{t('chat.title')}</h3>
        <div className="flex items-center gap-1">
          <button type="button"
            onClick={() => setShowSearch(!showSearch)}
            className="rounded p-1 hover:bg-accent"
          >
            <Search className="h-4 w-4" />
          </button>
          <button type="button" onClick={toggleChat} className="rounded p-1 hover:bg-accent">
            <ChevronDown className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Search bar */}
      {showSearch && (
        <div className="border-b px-3 py-2">
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('chat.searchMessages')}
            className="h-7 text-xs"
          />
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-3">
        {filteredMessages.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-xs text-muted-foreground text-center">
              {searchQuery ? t('chat.searchNoResults') : t('chat.noMessages')}
            </p>
          </div>
        ) : (
          filteredMessages.map((msg) => (
            <MessageBubble
              key={msg.messageId}
              message={msg}
              isOwn={msg.senderId === currentUserId}
              onReply={setReplyingTo}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Reply indicator */}
      {replyingTo && (
        <div className="flex items-center gap-2 border-t px-3 py-1.5 bg-muted/50">
          <Reply className="h-3 w-3 text-muted-foreground" />
          <span className="flex-1 truncate text-xs text-muted-foreground">
            {t('chat.replyTo', { user: replyingTo.senderName })}
          </span>
          <button type="button" onClick={() => setReplyingTo(null)} className="text-muted-foreground hover:text-foreground">
            <X className="h-3 w-3" />
          </button>
        </div>
      )}

      {/* Input */}
      <div className="flex items-center gap-2 border-t px-3 py-2">
        <Input
          ref={inputRef}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t('chat.placeholder')}
          className="h-8 text-sm"
        />
        <Button
          size="sm"
          className="h-8 w-8 shrink-0 p-0"
          onClick={handleSend}
          disabled={!inputValue.trim()}
        >
          <Send className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
