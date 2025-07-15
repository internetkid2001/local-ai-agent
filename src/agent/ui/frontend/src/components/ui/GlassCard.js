import React from 'react';

/**
 * GlassCard - A reusable component with glass morphism styling
 * Extracted from free-cluely-main design patterns
 */
const GlassCard = ({ 
  children, 
  className = '', 
  variant = 'default',
  blur = 'md',
  padding = 'p-4',
  onClick,
  hover = true
}) => {
  // Define variant styles
  const variants = {
    default: 'bg-black/60 border-white/10',
    light: 'bg-white/10 border-white/20',
    dark: 'bg-black/80 border-white/5',
    accent: 'bg-blue-500/20 border-blue-500/30',
    error: 'bg-red-500/20 border-red-500/30',
    success: 'bg-green-500/20 border-green-500/30'
  };

  // Define blur levels
  const blurLevels = {
    none: '',
    sm: 'backdrop-blur-sm',
    md: 'backdrop-blur-md',
    lg: 'backdrop-blur-lg',
    xl: 'backdrop-blur-xl'
  };

  // Build the complete className
  const baseClasses = `
    ${variants[variant] || variants.default}
    ${blurLevels[blur] || blurLevels.md}
    rounded-lg
    border
    transition-all
    duration-200
    ${hover ? 'hover:bg-white/20 hover:border-white/20' : ''}
    ${onClick ? 'cursor-pointer' : ''}
    ${padding}
    ${className}
  `.trim().replace(/\s+/g, ' ');

  return (
    <div className={baseClasses} onClick={onClick}>
      {children}
    </div>
  );
};

// Glass Button Component
export const GlassButton = ({ 
  children, 
  onClick, 
  className = '', 
  size = 'md',
  variant = 'default',
  disabled = false
}) => {
  const sizes = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1.5 text-sm',
    lg: 'px-4 py-2 text-base'
  };

  const variants = {
    default: 'bg-white/10 hover:bg-white/20 text-white/70',
    primary: 'bg-blue-500/20 hover:bg-blue-500/30 text-blue-300',
    danger: 'bg-red-500/20 hover:bg-red-500/30 text-red-300',
    success: 'bg-green-500/20 hover:bg-green-500/30 text-green-300'
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        ${variants[variant] || variants.default}
        ${sizes[size] || sizes.md}
        backdrop-blur-sm
        rounded-md
        transition-colors
        duration-200
        disabled:opacity-50
        disabled:cursor-not-allowed
        ${className}
      `.trim().replace(/\s+/g, ' ')}
    >
      {children}
    </button>
  );
};

// Glass Input Component
export const GlassInput = ({
  value,
  onChange,
  placeholder,
  type = 'text',
  className = '',
  ...props
}) => {
  return (
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className={`
        bg-white/10
        backdrop-blur-sm
        border
        border-white/20
        rounded-md
        px-3
        py-2
        text-white
        placeholder:text-white/50
        focus:outline-none
        focus:border-white/40
        focus:bg-white/20
        transition-all
        duration-200
        ${className}
      `.trim().replace(/\s+/g, ' ')}
      {...props}
    />
  );
};

// Glass Badge Component
export const GlassBadge = ({ children, variant = 'default', className = '' }) => {
  const variants = {
    default: 'bg-white/10 text-white/70',
    info: 'bg-blue-500/20 text-blue-300',
    warning: 'bg-yellow-500/20 text-yellow-300',
    error: 'bg-red-500/20 text-red-300',
    success: 'bg-green-500/20 text-green-300'
  };

  return (
    <span
      className={`
        ${variants[variant] || variants.default}
        backdrop-blur-sm
        px-2
        py-0.5
        rounded
        text-xs
        font-medium
        ${className}
      `.trim().replace(/\s+/g, ' ')}
    >
      {children}
    </span>
  );
};

export default GlassCard;
