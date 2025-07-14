import React from 'react';
import { Wifi, WifiOff, Loader2, AlertTriangle } from 'lucide-react';
import { cn } from '../../lib/utils';

export function ConnectionStatus({ connectionState, className }) {
  const getStatusInfo = () => {
    switch (connectionState) {
      case 'Connected':
        return {
          icon: <Wifi className="w-3 h-3" />,
          text: 'Connected',
          color: 'text-green-400',
          bgColor: 'bg-green-500/20',
          borderColor: 'border-green-500/30'
        };
      case 'Connecting':
        return {
          icon: <Loader2 className="w-3 h-3 animate-spin" />,
          text: 'Connecting',
          color: 'text-yellow-400',
          bgColor: 'bg-yellow-500/20',
          borderColor: 'border-yellow-500/30'
        };
      case 'Disconnected':
        return {
          icon: <WifiOff className="w-3 h-3" />,
          text: 'Disconnected',
          color: 'text-red-400',
          bgColor: 'bg-red-500/20',
          borderColor: 'border-red-500/30'
        };
      case 'Error':
        return {
          icon: <AlertTriangle className="w-3 h-3" />,
          text: 'Error',
          color: 'text-red-400',
          bgColor: 'bg-red-500/20',
          borderColor: 'border-red-500/30'
        };
      default:
        return {
          icon: <WifiOff className="w-3 h-3" />,
          text: 'Unknown',
          color: 'text-gray-400',
          bgColor: 'bg-gray-500/20',
          borderColor: 'border-gray-500/30'
        };
    }
  };

  const status = getStatusInfo();

  return (
    <div className={cn(
      "flex items-center gap-2 px-2 py-1 rounded-lg border backdrop-blur-sm",
      status.bgColor,
      status.borderColor,
      className
    )}>
      <div className={status.color}>
        {status.icon}
      </div>
      <span className={cn("text-[11px] font-medium", status.color)}>
        {status.text}
      </span>
    </div>
  );
}