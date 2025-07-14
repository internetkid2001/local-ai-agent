const { app, BrowserWindow, Menu, Tray, nativeImage, ipcMain, shell, globalShortcut, screen } = require('electron');
const path = require('path');
const isDev = require('electron-is-dev');

let mainWindow;
let tray = null;
let isWindowVisible = false;
let windowPosition = null;
let windowSize = null;

function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const workArea = primaryDisplay.workAreaSize;
  
  // Create the browser window with floating transparent design
  mainWindow = new BrowserWindow({
    width: 450,
    height: 600,
    minWidth: 350,
    minHeight: 400,
    maxWidth: 800,
    x: Math.floor(workArea.width * 0.7), // Position on right side
    y: 50,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js')
    },
    show: false,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: true,
    movable: true,
    fullscreenable: false,
    hasShadow: false,
    backgroundColor: '#00000000',
    focusable: true,
    vibrancy: 'ultra-dark', // macOS only
    autoHideMenuBar: true,
  });

  // Platform-specific window settings
  if (process.platform === 'darwin') {
    mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
    mainWindow.setAlwaysOnTop(true, 'floating');
  } else if (process.platform === 'linux') {
    mainWindow.setSkipTaskbar(true);
    mainWindow.setAlwaysOnTop(true);
  }

  // Load the app
  const startUrl = isDev 
    ? 'http://localhost:3000' 
    : `file://${path.join(__dirname, 'build/index.html')}`;
  
  mainWindow.loadURL(startUrl);

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.showInactive(); // Show without stealing focus
    isWindowVisible = true;
    
    // Store initial position
    const bounds = mainWindow.getBounds();
    windowPosition = { x: bounds.x, y: bounds.y };
    windowSize = { width: bounds.width, height: bounds.height };
    
    // Open DevTools in development
    if (isDev) {
      mainWindow.webContents.openDevTools({ mode: 'detach' });
    }
  });

  // Handle window events
  mainWindow.on('closed', () => {
    mainWindow = null;
    isWindowVisible = false;
  });

  mainWindow.on('move', () => {
    if (mainWindow) {
      const bounds = mainWindow.getBounds();
      windowPosition = { x: bounds.x, y: bounds.y };
    }
  });

  mainWindow.on('resize', () => {
    if (mainWindow) {
      const bounds = mainWindow.getBounds();
      windowSize = { width: bounds.width, height: bounds.height };
    }
  });

  // Handle external links
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // Prevent new window creation
  mainWindow.webContents.on('new-window', (event, navigationUrl) => {
    event.preventDefault();
    shell.openExternal(navigationUrl);
  });

  // Hide dock icon on macOS
  if (process.platform === 'darwin') {
    app.dock?.hide();
  }
}

// Window management functions
function toggleMainWindow() {
  if (!mainWindow) {
    createWindow();
    return;
  }

  if (isWindowVisible && mainWindow.isVisible()) {
    hideMainWindow();
  } else {
    showMainWindow();
  }
}

function showMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    createWindow();
    return;
  }

  if (windowPosition && windowSize) {
    mainWindow.setBounds({
      x: windowPosition.x,
      y: windowPosition.y,
      width: windowSize.width,
      height: windowSize.height
    });
  }

  mainWindow.showInactive();
  mainWindow.focus();
  isWindowVisible = true;

  // Platform-specific focus handling
  if (process.platform === 'darwin') {
    mainWindow.setAlwaysOnTop(true, 'floating');
  }
}

function hideMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) return;

  const bounds = mainWindow.getBounds();
  windowPosition = { x: bounds.x, y: bounds.y };
  windowSize = { width: bounds.width, height: bounds.height };
  
  mainWindow.hide();
  isWindowVisible = false;
}

function moveWindow(direction) {
  if (!mainWindow || !isWindowVisible) return;

  const primaryDisplay = screen.getPrimaryDisplay();
  const workArea = primaryDisplay.workAreaSize;
  const bounds = mainWindow.getBounds();
  const step = Math.floor(workArea.width / 10);

  let newX = bounds.x;
  let newY = bounds.y;

  switch (direction) {
    case 'left':
      newX = Math.max(0, bounds.x - step);
      break;
    case 'right':
      newX = Math.min(workArea.width - bounds.width, bounds.x + step);
      break;
    case 'up':
      newY = Math.max(0, bounds.y - step);
      break;
    case 'down':
      newY = Math.min(workArea.height - bounds.height, bounds.y + step);
      break;
  }

  mainWindow.setPosition(newX, newY);
  windowPosition = { x: newX, y: newY };
}

function createTray() {
  // Simple tray without icon for now
  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show Local AI Agent',
      click: showMainWindow
    },
    {
      label: 'Hide Local AI Agent',
      click: hideMainWindow
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        app.isQuiting = true;
        app.quit();
      }
    }
  ]);
  
  // Create a simple tray (cross-platform)
  try {
    tray = new Tray(nativeImage.createEmpty());
    tray.setToolTip('Local AI Agent');
    tray.setContextMenu(contextMenu);
    
    tray.on('click', toggleMainWindow);
  } catch (error) {
    console.log('Tray not supported on this platform');
  }
}

function registerGlobalShortcuts() {
  // Main toggle shortcut (like Cluely's Cmd+B)
  globalShortcut.register('CommandOrControl+B', () => {
    console.log('Global shortcut triggered: Toggle window');
    toggleMainWindow();
  });

  // Window movement shortcuts
  globalShortcut.register('CommandOrControl+Left', () => {
    console.log('Global shortcut triggered: Move left');
    moveWindow('left');
  });

  globalShortcut.register('CommandOrControl+Right', () => {
    console.log('Global shortcut triggered: Move right');
    moveWindow('right');
  });

  globalShortcut.register('CommandOrControl+Up', () => {
    console.log('Global shortcut triggered: Move up');
    moveWindow('up');
  });

  globalShortcut.register('CommandOrControl+Down', () => {
    console.log('Global shortcut triggered: Move down');
    moveWindow('down');
  });

  // Hide shortcut
  globalShortcut.register('CommandOrControl+H', () => {
    console.log('Global shortcut triggered: Hide window');
    hideMainWindow();
  });

  // New chat shortcut
  globalShortcut.register('CommandOrControl+N', () => {
    console.log('Global shortcut triggered: New chat');
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('new-chat');
    }
  });
}

function createMenu() {
  const template = [
    {
      label: 'File',
      submenu: [
        {
          label: 'New Chat',
          accelerator: 'CmdOrCtrl+N',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.send('new-chat');
            }
          }
        },
        { type: 'separator' },
        {
          label: 'Toggle Window',
          accelerator: 'CmdOrCtrl+B',
          click: toggleMainWindow
        },
        {
          label: 'Hide Window',
          accelerator: 'CmdOrCtrl+H',
          click: hideMainWindow
        },
        { type: 'separator' },
        {
          label: 'Quit',
          accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
          click: () => {
            app.isQuiting = true;
            app.quit();
          }
        }
      ]
    },
    {
      label: 'Window',
      submenu: [
        {
          label: 'Move Left',
          accelerator: 'CmdOrCtrl+Left',
          click: () => moveWindow('left')
        },
        {
          label: 'Move Right',
          accelerator: 'CmdOrCtrl+Right',
          click: () => moveWindow('right')
        },
        {
          label: 'Move Up',
          accelerator: 'CmdOrCtrl+Up',
          click: () => moveWindow('up')
        },
        {
          label: 'Move Down',
          accelerator: 'CmdOrCtrl+Down',
          click: () => moveWindow('down')
        },
        { type: 'separator' },
        {
          label: 'Always on Top',
          type: 'checkbox',
          checked: true,
          click: (menuItem) => {
            if (mainWindow) {
              mainWindow.setAlwaysOnTop(menuItem.checked);
            }
          }
        }
      ]
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'About Local AI Agent',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.send('show-about');
            }
          }
        }
      ]
    }
  ];

  // macOS specific menu adjustments
  if (process.platform === 'darwin') {
    template.unshift({
      label: app.getName(),
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' }
      ]
    });

    // Window menu
    template[4].submenu = [
      { role: 'close' },
      { role: 'minimize' },
      { role: 'zoom' },
      { type: 'separator' },
      { role: 'front' }
    ];
  }

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// App event handlers
app.whenReady().then(() => {
  createWindow();
  createMenu();
  createTray();
  registerGlobalShortcuts();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  app.isQuiting = true;
  globalShortcut.unregisterAll();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

// IPC handlers for window management
ipcMain.handle('get-app-version', () => {
  return app.getVersion();
});

ipcMain.handle('get-platform', () => {
  return process.platform;
});

ipcMain.handle('toggle-window', () => {
  toggleMainWindow();
});

ipcMain.handle('hide-window', () => {
  hideMainWindow();
});

ipcMain.handle('show-window', () => {
  showMainWindow();
});

ipcMain.handle('move-window', (event, direction) => {
  moveWindow(direction);
});

ipcMain.handle('get-window-state', () => {
  return {
    isVisible: isWindowVisible,
    position: windowPosition,
    size: windowSize
  };
});

// Handle window close event properly
app.on('ready', () => {
  if (mainWindow) {
    mainWindow.on('close', (event) => {
      if (!app.isQuiting) {
        event.preventDefault();
        hideMainWindow();
        return false;
      }
    });
  }
});