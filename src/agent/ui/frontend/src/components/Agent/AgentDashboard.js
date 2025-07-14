import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardContent, CardTitle } from '../ui/card';
import { ConnectionStatus } from './ConnectionStatus';
import { 
  Brain, 
  Cpu, 
  Database, 
  Network, 
  Zap, 
  Bot,
  MonitorSpeaker,
  FileText,
  Settings,
  Activity
} from 'lucide-react';
import { cn } from '../../lib/utils';

export function AgentDashboard({ connectionState, isConnected, agentStatus = {}, mcpServers = {} }) {
  const [systemStats, setSystemStats] = useState({
    localModels: ['Llama 3.1 8B', 'Mistral 7B'],
    cloudModels: ['Claude Sonnet 4', 'GPT-4'],
    mcpServers: ['Filesystem', 'Desktop', 'System', 'AI Bridge'],
    activeTasks: 0,
    memoryUsage: '2.1GB',
    uptime: '2h 34m'
  });

  // Mock real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setSystemStats(prev => ({
        ...prev,
        activeTasks: Math.floor(Math.random() * 5),
        uptime: `${Math.floor(Math.random() * 12)}h ${Math.floor(Math.random() * 60)}m`
      }));
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const StatCard = ({ icon: Icon, title, value, status = 'normal', className }) => (
    <Card className={cn('p-4 transition-all duration-200 hover:scale-105', className)}>
      <div className="flex items-center gap-3">
        <div className={cn(
          'p-2 rounded-lg',
          status === 'active' && 'bg-green-500/20 text-green-400',
          status === 'warning' && 'bg-yellow-500/20 text-yellow-400',
          status === 'error' && 'bg-red-500/20 text-red-400',
          status === 'normal' && 'bg-blue-500/20 text-blue-400'
        )}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-white/60 text-xs font-medium">{title}</div>
          <div className="text-white text-sm font-semibold truncate">{value}</div>
        </div>
      </div>
    </Card>
  );

  const ModelStatus = ({ models, type, isLocal = false }) => (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <div className={cn(
          'w-2 h-2 rounded-full',
          isLocal ? 'bg-green-400' : 'bg-blue-400'
        )} />
        <span className="text-white/80 text-sm font-medium">
          {type} Models {isLocal ? '(Local)' : '(Cloud)'}
        </span>
      </div>
      <div className="space-y-1 ml-4">
        {models.map((model, index) => (
          <div key={index} className="flex items-center justify-between text-xs">
            <span className="text-white/60">{model}</span>
            <div className={cn(
              'w-1.5 h-1.5 rounded-full',
              isConnected ? 'bg-green-400' : 'bg-gray-400'
            )} />
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="space-y-4">
      {/* Header Status */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl">
                <Brain className="w-6 h-6 text-white" />
              </div>
              <div>
                <div className="text-xl">AI Agent Status</div>
                <div className="text-xs text-white/60 font-normal">
                  Intelligent Automation System
                </div>
              </div>
            </CardTitle>
            <ConnectionStatus connectionState={connectionState} />
          </div>
        </CardHeader>
      </Card>

      {/* Quick Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          icon={Activity}
          title="Active Tasks"
          value={systemStats.activeTasks}
          status={systemStats.activeTasks > 0 ? 'active' : 'normal'}
        />
        <StatCard
          icon={Database}
          title="Memory Usage"
          value={systemStats.memoryUsage}
          status="normal"
        />
        <StatCard
          icon={Zap}
          title="Uptime"
          value={systemStats.uptime}
          status="active"
        />
        <StatCard
          icon={Network}
          title="MCP Servers"
          value={`${systemStats.mcpServers.length} Active`}
          status={isConnected ? 'active' : 'error'}
        />
      </div>

      {/* AI Models Status */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Cpu className="w-4 h-4" />
              AI Models
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <ModelStatus 
              models={systemStats.localModels} 
              type="Local" 
              isLocal={true} 
            />
            <ModelStatus 
              models={systemStats.cloudModels} 
              type="Cloud" 
              isLocal={false} 
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <MonitorSpeaker className="w-4 h-4" />
              MCP Servers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.keys(mcpServers).length > 0 ? (
                Object.entries(mcpServers).map(([serverName, serverInfo]) => (
                  <div key={serverName} className="flex items-center justify-between p-2 rounded-lg bg-white/5">
                    <div className="flex items-center gap-2">
                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        serverInfo.status === 'active' ? 'bg-green-400' : 'bg-yellow-400'
                      )} />
                      <span className="text-white/80 text-sm capitalize">{serverName}</span>
                    </div>
                    <span className={cn(
                      "text-xs",
                      serverInfo.status === 'active' ? 'text-green-400' : 'text-yellow-400'
                    )}>
                      {serverInfo.status || 'Unknown'}
                    </span>
                  </div>
                ))
              ) : (
                systemStats.mcpServers.map((server, index) => (
                  <div key={index} className="flex items-center justify-between p-2 rounded-lg bg-white/5">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-green-400 rounded-full" />
                      <span className="text-white/80 text-sm">{server}</span>
                    </div>
                    <span className="text-green-400 text-xs">Active</span>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* System Capabilities */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Bot className="w-4 h-4" />
            Agent Capabilities
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { name: 'Natural Language', icon: FileText },
              { name: 'Code Generation', icon: Cpu },
              { name: 'Task Automation', icon: Zap },
              { name: 'System Control', icon: Settings }
            ].map((capability, index) => (
              <div key={index} className="flex items-center gap-2 p-2 rounded-lg bg-blue-500/10">
                <capability.icon className="w-4 h-4 text-blue-400" />
                <span className="text-white/80 text-xs">{capability.name}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}