import React, { useState } from 'react';

/**
 * Advanced Glass Morphism Card Component
 * Inspired by Horizon Overlay's glass effects
 */
export const GlassCardAdvanced = ({ 
  children, 
  className = '', 
  variant = 'default',
  elevation = 'medium',
  glow = false,
  draggable = false,
  onDragStart,
  onDragEnd,
  style = {}
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isHovering, setIsHovering] = useState(false);

  const variants = {
    default: {
      bg: 'bg-white/10 dark:bg-white/5',
      border: 'border-white/20 dark:border-white/10',
      glow: 'shadow-white/20'
    },
    elevated: {
      bg: 'bg-white/15 dark:bg-white/8',
      border: 'border-white/30 dark:border-white/15',
      glow: 'shadow-white/30'
    },
    dark: {
      bg: 'bg-black/20 dark:bg-black/40',
      border: 'border-white/10 dark:border-white/5',
      glow: 'shadow-black/50'
    }
  };

  const elevations = {
    low: 'shadow-lg',
    medium: 'shadow-xl',
    high: 'shadow-2xl'
  };

  const currentVariant = variants[variant] || variants.default;

  const handleDragStart = (e) => {
    setIsDragging(true);
    if (onDragStart) onDragStart(e);
  };

  const handleDragEnd = (e) => {
    setIsDragging(false);
    if (onDragEnd) onDragEnd(e);
  };

  return (
    <div
      className={`
        relative
        ${currentVariant.bg}
        backdrop-blur-xl
        ${currentVariant.border}
        border
        rounded-2xl
        ${elevations[elevation]}
        transition-all duration-300
        ${isDragging ? 'scale-105 rotate-1' : ''}
        ${isHovering && !isDragging ? 'scale-[1.02]' : ''}
        ${glow ? `${currentVariant.glow} shadow-2xl` : ''}
        ${draggable ? 'cursor-move' : ''}
        ${className}
      `.trim().replace(/\s+/g, ' ')}
      style={{
        ...style,
        boxShadow: isDragging 
          ? '0 25px 50px -12px rgba(0, 0, 0, 0.5)' 
          : undefined
      }}
      draggable={draggable}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      {/* Gradient overlay for depth */}
      <div className="absolute inset-0 rounded-2xl overflow-hidden pointer-events-none">
        <div 
          className="absolute inset-0 opacity-30 dark:opacity-20"
          style={{
            background: `
              radial-gradient(
                ellipse at top,
                rgba(255, 255, 255, 0.2) 0%,
                transparent 60%
              )
            `
          }}
        />
      </div>

      {/* Drag handle indicator (if draggable) */}
      {draggable && (
        <div className="absolute top-2 left-1/2 transform -translate-x-1/2">
          <div className={`
            flex gap-1 p-1
            ${isDragging ? 'opacity-60' : 'opacity-30'}
            transition-opacity
          `}>
            <div className="w-1 h-1 bg-white rounded-full" />
            <div className="w-1 h-1 bg-white rounded-full" />
            <div className="w-1 h-1 bg-white rounded-full" />
          </div>
        </div>
      )}

      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
};

/**
 * Context Card Component
 * Fixed-width card inspired by Horizon Overlay
 */
export const ContextCard = ({ 
  text, 
  tags = [], 
  onTagClick,
  onDelete,
  draggable = true 
}) => {
  const [isDragging, setIsDragging] = useState(false);

  // Limit text to 150 words
  const limitedText = text.split(' ').slice(0, 150).join(' ') + 
    (text.split(' ').length > 150 ? '...' : '');

  return (
    <GlassCardAdvanced
      draggable={draggable}
      className="w-64 p-4"
      onDragStart={() => setIsDragging(true)}
      onDragEnd={() => setIsDragging(false)}
      elevation={isDragging ? 'high' : 'medium'}
    >
      <div className="space-y-3">
        {/* Text content */}
        <p className="text-sm text-gray-300 leading-relaxed">
          {limitedText}
        </p>

        {/* Tags */}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {tags.map((tag, index) => (
              <TagChip
                key={index}
                tag={tag}
                onClick={() => onTagClick && onTagClick(tag)}
              />
            ))}
          </div>
        )}

        {/* Delete button */}
        {onDelete && (
          <button
            onClick={onDelete}
            className="absolute top-2 right-2 p-1 rounded-full
                     bg-red-500/20 hover:bg-red-500/30
                     text-red-300 hover:text-red-200
                     transition-all opacity-0 hover:opacity-100
                     parent-hover:opacity-100"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
    </GlassCardAdvanced>
  );
};

/**
 * Tag Chip Component
 */
export const TagChip = ({ tag, onClick, removable = false, onRemove }) => {
  const { name, color = '#FA934E' } = tag;

  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1 px-2 py-1 rounded-md
                 text-xs font-medium transition-all
                 hover:scale-105 active:scale-95"
      style={{
        backgroundColor: `${color}33`,
        color: color,
        borderColor: `${color}66`,
        borderWidth: '1px',
        borderStyle: 'solid'
      }}
    >
      <span>{name}</span>
      {removable && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove && onRemove();
          }}
          className="ml-1 hover:opacity-70"
        >
          ×
        </button>
      )}
    </button>
  );
};

/**
 * Shimmer Text Component for thinking indicators
 */
export const ShimmerText = ({ text, className = '' }) => {
  return (
    <div className={`relative inline-block ${className}`}>
      <span className="relative z-10">{text}</span>
      <div 
        className="absolute inset-0 -z-10"
        style={{
          background: `
            linear-gradient(
              90deg,
              transparent 0%,
              rgba(255, 255, 255, 0.3) 50%,
              transparent 100%
            )
          `,
          backgroundSize: '200% 100%',
          animation: 'shimmer 2s ease-in-out infinite'
        }}
      />
    </div>
  );
};

// Add shimmer animation to global styles
const style = document.createElement('style');
style.textContent = `
  @keyframes shimmer {
    0% { background-position: -100% 0; }
    100% { background-position: 100% 0; }
  }
  
  .parent-hover\\:opacity-100:hover .hover\\:opacity-100,
  .parent-hover\\:opacity-100:hover [class*="parent-hover\\:opacity-100"] {
    opacity: 1;
  }
`;
document.head.appendChild(style);

export default GlassCardAdvanced;
