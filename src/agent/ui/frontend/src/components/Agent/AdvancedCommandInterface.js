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
  Zap,
  Camera,
  Search,
  Play,
  Settings
} from 'lucide-react';
import { cn } from '../../lib/utils';

export function AdvancedCommandInterface({ 
  onSendMessage, 
  onSendMCPCommand,
  disabled = false, 
  isLoading = false,
  mcpServers = {},
  agentStatus = {}
}) {
  const [input, setInput] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedMode, setSelectedMode] = useState('automation');
  const inputRef = useRef(null);

  const modes = [
    { id: 'automation', name: 'Automation', icon: Zap, color: 'blue' },
    { id: 'analysis', name: 'Analysis', icon: Search, color: 'purple' },
    { id: 'chat', name: 'Chat', icon: Terminal, color: 'green' }
  ];

  const suggestions = [
    {
      category: 'File Operations',
      icon: Folder,
      color: 'blue',
      commands: [
        'Take a screenshot and organize my desktop files by type',
        'Find all Python projects in my home directory',
        'Create a backup of documents modified today',
        'Search for files containing "API key" and secure them'
      ]
    },
    {
      category: 'Desktop Automation',
      icon: Monitor,
      color: 'purple',
      commands: [
        'Take a screenshot every 30 minutes during work hours',
        'Monitor CPU usage and alert if above 80% for 5 minutes',
        'Automatically close unnecessary browser tabs',
        'Set up window layouts for my development workflow'
      ]
    },
    {
      category: 'AI-Powered Tasks',
      icon: Sparkles,
      color: 'green',
      commands: [
        'Analyze the current screen and suggest improvements',
        'Review my code files and identify potential issues',
        'Generate documentation for my latest project',
        'Explain the contents of my Downloads folder'
      ]
    },
    {
      category: 'System Intelligence',
      icon: Settings,
      color: 'orange',
      commands: [
        'Monitor system health and create a daily report',
        'Optimize running processes for better performance',
        'Analyze network activity and identify unusual patterns',
        'Clean up log files and temporary data automatically'
      ]
    }
  ];

  const quickActions = [
    { 
      name: 'Screenshot', 
      icon: Camera, 
      action: () => onSendMCPCommand('desktop', 'take_screenshot'),
      color: 'blue'
    },
    { 
      name: 'System Status', 
      icon: Monitor, 
      action: () => onSendMCPCommand('system', 'get_system_info'),
      color: 'green'
    },
    { 
      name: 'File Search', 
      icon: Search, 
      action: () => setInput('Search for files containing '),
      color: 'purple'
    }
  ];

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSendMessage(input, { 
        mode: selectedMode,
        mcp_enabled: true,
        context: { timestamp: Date.now() }
      });
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

  const getModeColor = (mode) => {
    const modeObj = modes.find(m => m.id === mode);
    return modeObj ? modeObj.color : 'blue';
  };

  return (
    <div className="space-y-3">
      {/* Mode Selector */}
      <div className="flex items-center gap-2 p-2 bg-black/20 rounded-lg">
        <span className="text-white/60 text-xs">Mode:</span>
        {modes.map((mode) => (
          <button
            key={mode.id}
            onClick={() => setSelectedMode(mode.id)}
            className={cn(
              "flex items-center gap-2 px-3 py-1 rounded-md text-xs transition-all duration-200",
              selectedMode === mode.id
                ? `bg-${mode.color}-500/20 text-${mode.color}-400 border border-${mode.color}-500/30`
                : "text-white/60 hover:text-white/80 hover:bg-white/5"
            )}
          >
            <mode.icon className="w-3 h-3" />
            {mode.name}
          </button>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="flex gap-2">
        {quickActions.map((action, index) => (
          <button
            key={index}
            onClick={action.action}
            disabled={disabled}
            className={cn(
              "flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition-all duration-200",
              `bg-${action.color}-500/10 hover:bg-${action.color}-500/20 text-${action.color}-400`,
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            <action.icon className="w-3 h-3" />
            {action.name}
          </button>
        ))}
      </div>

      {/* Suggestions Overlay */}
      {showSuggestions && (
        <div className="relative z-50">
          <Card className="max-h-96 overflow-y-auto">
            <CardContent className="p-3">
              <div className="flex items-center gap-2 mb-3 pb-2 border-b border-white/10">
                <Sparkles className="w-4 h-4 text-blue-400" />
                <span className="text-white/80 text-sm font-medium">
                  AI Automation Commands
                </span>
                <span className="text-white/50 text-xs ml-auto">
                  Powered by MCP
                </span>
              </div>
              
              <div className="space-y-3">
                {suggestions.map((category, categoryIndex) => (
                  <div key={categoryIndex}>
                    <div className="flex items-center gap-2 mb-2">
                      <category.icon className={`w-3 h-3 text-${category.color}-400`} />
                      <span className="text-white/60 text-xs font-medium">
                        {category.category}
                      </span>
                      <div className={`w-1 h-1 bg-${category.color}-400 rounded-full`} />
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
                  💡 <strong>Pro Tip:</strong> Commands automatically use the best available AI model and MCP servers for optimal results.
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
                <Terminal className={`w-4 h-4 text-${getModeColor(selectedMode)}-400`} />
                <span className="text-white/60 text-xs">
                  AI Command Interface - {modes.find(m => m.id === selectedMode)?.name} Mode
                </span>
                {!showSuggestions && (
                  <span className="text-white/40 text-xs ml-auto">
                    Press Tab for AI suggestions
                  </span>
                )}
              </div>
              
              <textarea
                ref={inputRef}
                className={cn(
                  "w-full bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl px-4 py-3",
                  "text-white placeholder-white/50 resize-none focus:outline-none transition-all duration-200 text-sm leading-relaxed",
                  `focus:ring-2 focus:ring-${getModeColor(selectedMode)}-500/50`,
                  disabled && "opacity-50 cursor-not-allowed"
                )}
                placeholder={`Describe what you want the AI to ${selectedMode === 'automation' ? 'automate' : selectedMode === 'analysis' ? 'analyze' : 'help with'}... (e.g., 'take a screenshot and organize my files')`}
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
              
              {/* Status Indicators */}
              <div className="flex items-center gap-3 mt-2">
                <div className="flex items-center gap-1">
                  <div className={cn(
                    "w-2 h-2 rounded-full",
                    agentStatus.status === 'running' ? 'bg-green-400' : 'bg-yellow-400'
                  )} />
                  <span className="text-green-400 text-xs">
                    AI Agent {agentStatus.status || 'Ready'}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <div className={cn(
                    "w-2 h-2 rounded-full",
                    Object.keys(mcpServers).length > 0 ? 'bg-blue-400' : 'bg-gray-400'
                  )} />
                  <span className="text-blue-400 text-xs">
                    {Object.keys(mcpServers).length} MCP Servers
                  </span>
                </div>
              </div>
            </div>
            
            <div className="flex flex-col gap-2">
              <button
                type="submit"
                disabled={!input.trim() || disabled || isLoading}
                className={cn(
                  "flex items-center justify-center w-12 h-12 rounded-xl",
                  `bg-gradient-to-r from-${getModeColor(selectedMode)}-600 to-purple-600`,
                  `hover:from-${getModeColor(selectedMode)}-500 hover:to-purple-500`,
                  "text-white transition-all duration-200 shadow-lg",
                  "disabled:opacity-50 disabled:cursor-not-allowed"
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
                title="Toggle AI suggestions"
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