"use client";

import React, { useState, useEffect, useRef, FormEvent, memo } from 'react';
import { Loader2, Send } from 'lucide-react';
import { cn } from "../../lib/utils";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { apiClient } from "@/lib/api";

interface Message {
  id: string;
  text: string;
  senderId: string;
  timestamp: Date;
}

const USER_ID = 'user123';
const BOT_ID = 'bot';
const SESSION_ID = 'mood_chat_session';
const BOT_GREETING: Message = {
  id: '1',
  text: 'Hello! How are you feeling today?',
  senderId: BOT_ID,
  // Note: timestamp will be set on the client after mount to avoid SSR hydration mismatches
  timestamp: new Date(0),
};

const ChatMessage = memo(({ message, isCurrentUser }: { message: Message; isCurrentUser: boolean }) => {
  const senderName = isCurrentUser ? 'You' : message.senderId;
  const avatarFallback = senderName.slice(0, 2).toUpperCase();

  return (
    <div
      className={cn(
        "flex items-end gap-3",
        isCurrentUser && "justify-end"
      )}
    >
      {!isCurrentUser && (
        <Avatar className="h-8 w-8">
          <AvatarFallback>{avatarFallback}</AvatarFallback>
        </Avatar>
      )}
      <div
        className={cn(
          "max-w-[80%] flex flex-col rounded-xl p-3",
          isCurrentUser
            ? "bg-primary text-primary-foreground rounded-br-none"
            : "bg-muted text-muted-foreground rounded-bl-none"
        )}
      >
        <p className="text-sm">{message.text}</p>
        <p className="text-xs mt-1 self-end opacity-70">
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
      {isCurrentUser && (
        <Avatar className="h-8 w-8">
          <AvatarFallback>{avatarFallback}</AvatarFallback>
        </Avatar>
      )}
    </div>
  );
});
ChatMessage.displayName = 'ChatMessage';


const MoodIndex = () => {
  // Start with no messages on the server to avoid SSR/client time mismatches
  const [messages, setMessages] = useState<Message[]>([]);
  // Inject bot greeting on client after mount with a client-side timestamp
  useEffect(() => {
    setMessages([{ ...BOT_GREETING, timestamp: new Date() }]);
  }, []);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const listRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLDivElement>(null);
  const [composerHeight, setComposerHeight] = useState(0);
  useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    // Only scroll down if the last message was from the current user.
    // This prevents the view from scrolling down on a bot response.
    if (lastMessage?.senderId === USER_ID) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);


  // Measure composer height dynamically
  useEffect(() => {
    if (!composerRef.current || typeof window === 'undefined') return;
    const el = composerRef.current;
    setComposerHeight(el.getBoundingClientRect().height);
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setComposerHeight(entry.contentRect.height);
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Reliable auto-scroll helper
  const scrollToBottom = () => {
    if (typeof window === 'undefined') return;
    requestAnimationFrame(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    });
  };

  // Scroll on new messages
  useEffect(() => {
    scrollToBottom();
  }, [messages.length]);

  // Scroll when images/avatars load
  useEffect(() => {
    const container = listRef.current;
    if (!container) return;
    const imgs = Array.from(container.querySelectorAll('img')) as HTMLImageElement[];
    const handlers: Array<() => void> = [];
    imgs.forEach((img) => {
      const handler = () => scrollToBottom();
      handlers.push(handler);
      if (!img.complete) img.addEventListener('load', handler);
    });
    return () => {
      imgs.forEach((img, i) => img.removeEventListener('load', handlers[i]));
    };
  }, [messages.length]);

  // Scroll on viewport/keyboard resize (mobile browsers)
  useEffect(() => {
    const onResize = () => scrollToBottom();
    window.addEventListener('resize', onResize);
    // iOS/Android visualViewport support
    const vv: VisualViewport | null | undefined =
      typeof window !== 'undefined' ? window.visualViewport : undefined;
    vv?.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      vv?.removeEventListener('resize', onResize);
    };
  }, []);


  const handleSendMessage = async (e: FormEvent) => {
    e.preventDefault();
    if (input.trim() === '' || loading) return;
  
    const newMessage: Message = {
      id: Date.now().toString(),
      text: input,
      senderId: USER_ID,
      timestamp: new Date(),
    };
  
    setMessages((prev) => [...prev, newMessage]);
    const currentInput = input;
    setInput('');
    setLoading(true);
  
    try {
      // Use agentic orchestrator chat endpoint
      const data = await apiClient.chat(SESSION_ID, currentInput, { user_id: USER_ID });
      const botResponse: Message = {
        id: (Date.now() + 1).toString(),
        text: data.text || "I'm here to support you. What's on your mind right now?",
        senderId: BOT_ID,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botResponse]);
    } catch (error) {
      console.error('Chat API failed:', error);
      const fallbackResponse: Message = {
        id: (Date.now() + 1).toString(),
        text: "I'm having trouble connecting right now, but I want you to know that your feelings matter and support is available.",
        senderId: BOT_ID,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, fallbackResponse]);
    } finally {
      setLoading(false);
    }
  };
  return (
    <div className="min-h-dvh flex flex-col">
      <div className="container mx-auto px-4 py-4 max-w-4xl flex-1 flex">
        <div className="w-full flex flex-col rounded-xl shadow-md bg-card border overflow-hidden">
          <div className="bg-muted/50 p-4 border-b">
            <h1 className="text-lg font-semibold text-center">Mood Journal</h1>
          </div>

          {/* Scrollable list fills available height; padding-bottom matches composer height */}
          <div
            ref={listRef}
            className="flex-1 overflow-y-auto p-4"
            style={{ paddingBottom: composerHeight ? composerHeight + 16 : 80 }}
          >
            <div className="flex flex-col space-y-4 pr-2">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} isCurrentUser={msg.senderId === USER_ID} />
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Composer is sticky to bottom (inside card) and self-measures height */}
          <div ref={composerRef} className="sticky bottom-0 bg-card/95 backdrop-blur supports-backdrop-filter:bg-card/80 border-t p-4">
            <form onSubmit={handleSendMessage} className="flex w-full items-center gap-2">
              <Input
                placeholder="Type your message..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
                className="flex-1"
              />
              <Button size="icon" type="submit" disabled={loading || input.trim() === ''} className="shrink-0">
                {loading ? <Loader2 className="animate-spin" /> : <Send size={20} />}
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MoodIndex