'use client';

/**
 * AI Terminal - System Console
 *
 * Collapsed bar at the bottom that expands on click.
 * Dark terminal aesthetic with green/amber text.
 */

import React, { useState, useRef, useEffect } from 'react';

interface Message {
  type: 'user' | 'system' | 'ai';
  content: string;
  timestamp: Date;
}

export function AITerminal() {
  const [expanded, setExpanded] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      type: 'system',
      content: 'LitDocket AI Terminal v1.0 - Type a question about your cases or deadlines',
      timestamp: new Date(),
    },
  ]);
  const [isProcessing, setIsProcessing] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (expanded && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, expanded]);

  // Focus input when expanded
  useEffect(() => {
    if (expanded && inputRef.current) {
      inputRef.current.focus();
    }
  }, [expanded]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isProcessing) return;

    const userMessage: Message = {
      type: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsProcessing(true);

    // Simulate AI response (replace with actual API call)
    setTimeout(() => {
      const aiMessage: Message = {
        type: 'ai',
        content: 'AI assistant is not yet connected. This terminal will provide intelligent case analysis once configured.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);
      setIsProcessing(false);
    }, 500);
  };

  const toggleExpanded = () => {
    setExpanded(!expanded);
  };

  return (
    <div className="cockpit-terminal">
      {/* Collapsed Bar */}
      {!expanded && (
        <div className="terminal-collapsed" onClick={toggleExpanded}>
          <div className="flex items-center gap-3">
            <span className="text-terminal-green font-mono text-sm">{'>'}_</span>
            <span className="text-terminal-text font-mono text-sm">
              AI Terminal
            </span>
            <span className="text-terminal-amber font-mono text-xs">
              [Click to expand]
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-terminal-green"></span>
            <span className="text-terminal-text font-mono text-xs">READY</span>
          </div>
        </div>
      )}

      {/* Expanded Terminal */}
      {expanded && (
        <div className="terminal">
          {/* Terminal Header */}
          <div
            className="flex items-center justify-between px-4 py-2 border-b border-gray-700 cursor-pointer"
            onClick={toggleExpanded}
          >
            <div className="flex items-center gap-3">
              <span className="text-terminal-green font-mono text-sm">{'>'}_</span>
              <span className="text-terminal-text font-mono text-sm">
                AI Terminal
              </span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-terminal-amber font-mono text-xs">
                [Click to collapse]
              </span>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-terminal-green"></span>
                <span className="text-terminal-text font-mono text-xs">READY</span>
              </div>
            </div>
          </div>

          {/* Messages Area */}
          <div className="terminal-expanded">
            {messages.map((msg, idx) => (
              <div key={idx} className="mb-2 font-mono text-sm">
                {msg.type === 'system' && (
                  <div className="text-terminal-amber">[SYSTEM] {msg.content}</div>
                )}
                {msg.type === 'user' && (
                  <div className="text-terminal-text">
                    <span className="text-terminal-amber">{'>'} </span>
                    {msg.content}
                  </div>
                )}
                {msg.type === 'ai' && (
                  <div className="text-terminal-green pl-2">{msg.content}</div>
                )}
              </div>
            ))}
            {isProcessing && (
              <div className="text-terminal-green font-mono text-sm animate-pulse">
                Processing...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <form onSubmit={handleSubmit} className="flex items-center px-4 py-2 border-t border-gray-700 bg-terminal-bg">
            <span className="text-terminal-amber font-mono text-sm mr-2">{'>'}</span>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your cases, deadlines, or documents..."
              className="terminal-input flex-1"
              disabled={isProcessing}
            />
            {isProcessing && <span className="terminal-cursor" />}
          </form>
        </div>
      )}
    </div>
  );
}

export default AITerminal;
