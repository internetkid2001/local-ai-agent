import React, { useState, useRef, useEffect } from 'react';
import { Card, CardContent } from '../ui/card';
import { 
  Send, 
  Loader2, 
  Terminal, 
  Sparkles, 
  FileText, 
  Folder,
  Monitor,
  Code,
  Zap
} from 'lucide-react';
import { cn } from '../../lib/utils';

export function CommandInterface({ onSendMessage, disabled = false, isLoading = false }) {
  const [input, setInput] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const inputRef = useRef(null);

  const suggestions = [
    {
      category: 'File Operations',
      icon: Folder,
      commands: [
        'Organize my Downloads folder by file type',
        'Find all Python projects modified this week',
        'Create a backup of my important documents'
      ]
    },
    {
      category: 'System Automation',
      icon: Monitor,
      commands: [
        'Take a screenshot every hour while I\'m working',
        'Monitor CPU usage and alert if it goes above 80%',
        'Clean up temporary files older than 7 days'
      ]
    },
    {
      category: 'Development',
      icon: Code,
      commands: [
        'Review the code in my current project',
        'Set up a new React project with TypeScript',
        'Find and fix potential security issues'
      ]
    },
    {
      category: 'AI Tasks',
      icon: Sparkles,
      commands: [
        'Analyze this document and summarize key points',
        'Generate unit tests for my Python functions',
        'Explain this complex code to me'
      ]
    }
  ];

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSendMessage(input);
      setInput('');
      setShowSuggestions(false);
    }
  };

  const handleSuggestionClick = (command) => {
    setInput(command);
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    } else if (e.key === 'Tab' && !showSuggestions) {
      e.preventDefault();
      setShowSuggestions(true);
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
  };

  const handleFocus = () => {
    if (!input.trim()) {
      setShowSuggestions(true);
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 120) + 'px';
    }
  }, [input]);

  return (
    <div className="relative">
      {/* Suggestions Overlay */}
      {showSuggestions && (
        <div className="absolute bottom-full left-0 right-0 mb-2 z-50">
          <Card className="max-h-96 overflow-y-auto">
            <CardContent className="p-3">
              <div className="flex items-center gap-2 mb-3 pb-2 border-b border-white/10">
                <Terminal className="w-4 h-4 text-blue-400" />
                <span className="text-white/80 text-sm font-medium">
                  AI Command Suggestions
                </span>
                <span className="text-white/50 text-xs ml-auto">
                  Press Tab or click to explore
                </span>
              </div>
              
              <div className="space-y-3">
                {suggestions.map((category, categoryIndex) => (
                  <div key={categoryIndex}>
                    <div className="flex items-center gap-2 mb-2">
                      <category.icon className="w-3 h-3 text-white/60" />
                      <span className="text-white/60 text-xs font-medium">
                        {category.category}
                      </span>
                    </div>
                    <div className="space-y-1 ml-5">
                      {category.commands.map((command, commandIndex) => (
                        <button
                          key={commandIndex}
                          onClick={() => handleSuggestionClick(command)}
                          className="w-full text-left p-2 rounded-lg text-white/80 text-xs hover:bg-white/10 transition-colors duration-200"
                        >
                          {command}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="mt-3 pt-2 border-t border-white/10">
                <div className="text-white/50 text-xs">
                  💡 <strong>Tip:</strong> Describe any task in natural language. The AI agent will determine the best approach using local or cloud models.
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Command Input */}
      <Card>
        <CardContent className="p-0">
          <form onSubmit={handleSubmit} className="flex gap-3 p-4">
            <div className="flex-1 relative">
              <div className="flex items-center gap-2 mb-2">
                <Terminal className="w-4 h-4 text-blue-400" />
                <span className="text-white/60 text-xs">AI Command Interface</span>
                {!showSuggestions && (
                  <span className="text-white/40 text-xs ml-auto">
                    Press Tab for suggestions
                  </span>
                )}
              </div>
              
              <textarea
                ref={inputRef}
                className={cn(
                  "w-full bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl px-4 py-3",
                  "text-white placeholder-white/50 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/50",
                  "transition-all duration-200 text-sm leading-relaxed",
                  disabled && "opacity-50 cursor-not-allowed"
                )}
                placeholder="Describe what you want me to do... (e.g., 'organize my desktop files' or 'analyze system performance')"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                onFocus={handleFocus}
                disabled={disabled}
                rows={1}
                style={{ 
                  minHeight: '52px',
                  maxHeight: '120px'
                }}
              />
              
              {/* Command Indicators */}
              <div className="flex items-center gap-2 mt-2">
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 bg-green-400 rounded-full" />
                  <span className="text-green-400 text-xs">Local Models Ready</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 bg-blue-400 rounded-full" />
                  <span className="text-blue-400 text-xs">Cloud Access Available</span>
                </div>
              </div>
            </div>
            
            <div className="flex flex-col gap-2">
              <button
                type="submit"
                disabled={!input.trim() || disabled || isLoading}
                className={cn(
                  "flex items-center justify-center w-12 h-12 rounded-xl",
                  "bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500",
                  "text-white transition-all duration-200 shadow-lg",
                  "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:from-blue-600 disabled:hover:to-purple-600"
                )}
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
              
              <button
                type="button"
                onClick={() => setShowSuggestions(!showSuggestions)}
                className="flex items-center justify-center w-12 h-10 rounded-lg bg-white/10 hover:bg-white/20 text-white/70 transition-colors duration-200"
                title="Toggle suggestions"
              >
                <Sparkles className="w-4 h-4" />
              </button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}