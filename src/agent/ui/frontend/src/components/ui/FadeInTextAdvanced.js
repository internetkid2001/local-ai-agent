import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';

/**
 * FadeInTextAdvanced Component
 * Advanced word-by-word fade-in for AI responses with markdown support
 * Inspired by Horizon Overlay's FadeInTextView
 */
export const FadeInTextAdvanced = ({
  text = "",
  wordDelay = 0.05,
  fadeInDuration = 0.4,
  className = "",
  onComplete,
  isStreaming = false
}) => {
  const [visibleWords, setVisibleWords] = useState([]);
  const [isHovering, setIsHovering] = useState(false);
  const [showCopyButton, setShowCopyButton] = useState(false);
  const wordsRef = useRef([]);
  const animationRef = useRef(null);
  const startTimeRef = useRef(null);

  // Parse text into words with their positions
  useEffect(() => {
    if (!text) {
      setVisibleWords([]);
      return;
    }

    // Split text into words while preserving markdown
    const words = text.split(/\s+/).filter(Boolean);
    wordsRef.current = words.map((word, index) => ({
      word,
      index,
      visible: false,
      opacity: 0
    }));

    // Reset animation
    startTimeRef.current = Date.now();
    animateWords();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [text]);

  const animateWords = useCallback(() => {
    const animate = () => {
      const currentTime = Date.now();
      const elapsed = (currentTime - startTimeRef.current) / 1000;
      let hasChanges = false;
      let allVisible = true;

      const updatedWords = wordsRef.current.map((wordObj, index) => {
        const wordStartTime = index * wordDelay;
        const progress = Math.max(0, Math.min(1, (elapsed - wordStartTime) / fadeInDuration));
        
        if (progress > 0 && !wordObj.visible) {
          hasChanges = true;
        }
        
        if (progress < 1) {
          allVisible = false;
        }

        return {
          ...wordObj,
          visible: progress > 0,
          opacity: progress
        };
      });

      if (hasChanges) {
        setVisibleWords([...updatedWords]);
      }

      if (!allVisible) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        setShowCopyButton(true);
        if (onComplete) onComplete();
      }
    };

    animate();
  }, [wordDelay, fadeInDuration, onComplete]);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(text);
    // Could add a toast notification here
  };

  const renderWords = () => {
    return visibleWords.map((wordObj, index) => (
      <span
        key={index}
        style={{
          opacity: wordObj.opacity,
          transition: `opacity ${fadeInDuration}s ease-out`,
          marginRight: '0.25em'
        }}
      >
        {wordObj.word}
      </span>
    ));
  };

  return (
    <div 
      className={`relative ${className}`}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      <div className="text-sm leading-relaxed">
        {isStreaming && visibleWords.length === 0 ? (
          <span className="inline-block animate-pulse">●●●</span>
        ) : (
          renderWords()
        )}
      </div>
      
      {/* Copy button */}
      {showCopyButton && isHovering && text && (
        <button
          onClick={copyToClipboard}
          className="absolute -right-8 top-0 p-1 rounded
                     bg-white/10 hover:bg-white/20
                     text-white/60 hover:text-white/80
                     transition-all duration-200"
          title="Copy to clipboard"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                  d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
          </svg>
        </button>
      )}
    </div>
  );
};

/**
 * MessageBubble Component
 * Styled message bubble for chat interface
 */
export const MessageBubble = ({ message, isUser, isThinking }) => {
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`
          max-w-[70%] px-4 py-3 rounded-2xl
          ${isUser 
            ? 'bg-purple-600/80 text-white ml-auto' 
            : 'bg-white/10 backdrop-blur-sm text-white'
          }
          ${isThinking ? 'animate-pulse' : ''}
        `}
      >
        {isThinking ? (
          <div className="flex items-center gap-2">
            <span className="text-sm italic opacity-70">Thinking</span>
            <span className="flex gap-1">
              <span className="w-1 h-1 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1 h-1 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1 h-1 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </span>
          </div>
        ) : (
          <FadeInTextAdvanced 
            text={message.content} 
            className="text-sm"
            wordDelay={isUser ? 0 : 0.03}
          />
        )}
      </div>
    </div>
  );
};

export default FadeInTextAdvanced;

