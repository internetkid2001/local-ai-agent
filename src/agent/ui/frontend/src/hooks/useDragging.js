import { useState, useRef, useCallback, useEffect } from 'react';

export function useDragging(initialPosition = { x: 50, y: 50 }) {
  const [isDragging, setIsDragging] = useState(false);
  const [position, setPosition] = useState(initialPosition);
  const offset = useRef({ x: 0, y: 0 });
  const dragStarted = useRef(false);

  const handleMouseDown = useCallback((e) => {
    // Prevent dragging if clicking on buttons or inputs
    if (e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT' || e.target.closest('button') || e.target.closest('input')) {
      return;
    }
    
    setIsDragging(true);
    dragStarted.current = true;
    offset.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    };
    e.preventDefault();
    e.stopPropagation();
    
    // Add visual feedback
    document.body.style.cursor = 'grabbing';
    document.body.style.userSelect = 'none';
  }, [position.x, position.y]);

  const handleMouseMove = useCallback((e) => {
    if (!isDragging || !dragStarted.current) return;
    
    const newX = e.clientX - offset.current.x;
    const newY = e.clientY - offset.current.y;
    
    // Constrain to window bounds
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    const elementWidth = 320; // Approximate window width
    const elementHeight = 600; // Approximate window height
    
    const constrainedX = Math.max(0, Math.min(newX, windowWidth - elementWidth));
    const constrainedY = Math.max(0, Math.min(newY, windowHeight - elementHeight));
    
    setPosition({
      x: constrainedX,
      y: constrainedY,
    });
    
    e.preventDefault();
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    dragStarted.current = false;
    
    // Remove visual feedback
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }, []);

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove, { passive: false });
      document.addEventListener('mouseup', handleMouseUp);
    } else {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      // Clean up on unmount
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  return {
    position,
    isDragging,
    handleMouseDown
  };
}
