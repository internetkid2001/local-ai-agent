import React, { useState, useEffect } from 'react';
import GlassCard from './GlassCard';
import { GlassButton } from './GlassCard';

/**
 * ScreenshotQueue Component
 * Manages screenshots with drag-and-drop and delete functionality.
 */
const ScreenshotQueue = ({ screenshots = [], onDelete }) => {
  const [localScreenshots, setLocalScreenshots] = useState(screenshots);

  useEffect(() => {
    setLocalScreenshots(screenshots);
  }, [screenshots]);

  const handleDelete = (path) => {
    onDelete(path);
    setLocalScreenshots((prev) => prev.filter(s => s.path !== path));
  };

  return (
    <div className="grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
      {localScreenshots.map(({ path, preview }) => (
        <GlassCard key={path} className="flex flex-col items-center">
          <img
            src={preview}
            alt="Screenshot Preview"
            className="rounded shadow-lg cursor-pointer mb-2"
          />
          <GlassButton variant="danger" onClick={() => handleDelete(path)}>
            Delete
          </GlassButton>
        </GlassCard>
      ))}
    </div>
  );
};

export default ScreenshotQueue;
