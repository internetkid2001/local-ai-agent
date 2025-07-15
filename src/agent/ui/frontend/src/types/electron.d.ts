declare global {
  interface Window {
    electronAPI?: {
      updateContentDimensions?: (dimensions: { width: number; height: number }) => void;
      hideWindow?: () => void;
      onNewChat?: (callback: () => void) => (() => void);
      showWindow?: () => void;
      minimizeWindow?: () => void;
      closeWindow?: () => void;
    };
  }
}

export {};
