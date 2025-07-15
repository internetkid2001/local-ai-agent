import React from 'react';
import { GlassCardAdvanced } from './ui/GlassCardAdvanced';

/**
 * Enhanced ScreenshotQueue Component
 * Displays screenshots with glass morphism styling
 */
const ScreenshotQueueEnhanced = ({ screenshots = [], onDelete }) => {
  return (
    <GlassCardAdvanced className="p-4" variant="default">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Screenshots</h3>
        <span className="text-xs text-white/60">{screenshots.length} captured</span>
      </div>
      
      {screenshots.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-4xl mb-2 opacity-30">📸</div>
          <p className="text-gray-400 text-sm">No screenshots yet</p>
          <p className="text-gray-500 text-xs mt-1">Press Ctrl+S to capture</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {screenshots.map(screenshot => (
            <div key={screenshot.id} className="relative">
              <GlassCardAdvanced 
                className="overflow-hidden p-0 group"
                elevation="low"
              >
                <div className="relative">
                  <img 
                    src={screenshot.dataUrl} 
                    alt={screenshot.name}
                    className="w-full h-32 object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                  <div className="absolute bottom-0 left-0 right-0 p-2">
                    <p className="text-xs text-white truncate font-medium">
                      {screenshot.name}
                    </p>
                    <p className="text-xs text-white/60">
                      {new Date(screenshot.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
                {onDelete && (
                  <button
                    onClick={() => onDelete(screenshot.id)}
                    className="absolute top-2 right-2 w-7 h-7 
                             bg-red-500/20 backdrop-blur-sm border border-red-500/30
                             hover:bg-red-500/40 hover:border-red-500/50
                             rounded-full flex items-center justify-center 
                             opacity-0 group-hover:opacity-100 
                             transition-all duration-200"
                    title="Delete screenshot"
                  >
                    <span className="text-red-200 text-sm font-bold">×</span>
                  </button>
                )}
              </GlassCardAdvanced>
            </div>
          ))}
        </div>
      )}
    </GlassCardAdvanced>
  );
};

export default ScreenshotQueueEnhanced;
