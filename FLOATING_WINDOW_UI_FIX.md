# Replicating Floating Window UI from `free-cluely-main` to `local-ai-agent`

## Issue

The goal is to make the floating window UI in the `/home/vic/Documents/CODE/local-ai-agent/` Electron application look identical to the UI found in the `/home/vic/Documents/CODE/free-cluely-main` project. This involves aligning the frontend technologies, styling, and component structure.

## Analysis of `free-cluely-main` UI

The `free-cluely-main` project utilizes the following key technologies for its frontend:

*   **Framework**: React
*   **Language**: TypeScript
*   **Styling**: Tailwind CSS (with custom configurations for fonts, animations, and keyframes)
*   **UI Components**: Radix UI (specifically `@radix-ui/react-toast` for toast notifications)
*   **State Management/Data Fetching**: `react-query`
*   **Electron Integration**: Custom `window.electronAPI` for inter-process communication (IPC) between the renderer process (UI) and the main Electron process.

## Proposed Solution

To achieve an identical look and feel, the `local-ai-agent` project's frontend needs to adopt the same technologies and replicate the relevant UI structure and logic.

### Steps to Implement:

1.  **Verify/Set Up Frontend Environment in `local-ai-agent`**:
    *   Ensure `local-ai-agent` is configured to use React and TypeScript. If not, you will need to set up a React/TypeScript frontend within the Electron project (e.g., using Vite, Create React App, or a similar build tool).
    *   Install necessary core dependencies: `react`, `react-dom`, `typescript`, `@types/react`, `@types/react-dom`.

2.  **Integrate Tailwind CSS**:
    *   **Copy Configuration**: Copy `tailwind.config.js` and `postcss.config.js` (if it exists in `free-cluely-main`) from `/home/vic/Documents/CODE/free-cluely-main/` to your `local-ai-agent` project's root directory.
    *   **Install Dependencies**: Install Tailwind CSS and its peer dependencies:
        ```bash
        npm install -D tailwindcss postcss autoprefixer
        npx tailwindcss init -p # This will create tailwind.config.js and postcss.config.js if you haven't copied them
        ```
    *   **Configure `content`**: Ensure the `content` array in `tailwind.config.js` correctly points to all your React component files (`./src/**/*.{js,jsx,ts,tsx}`).
    *   **Import Tailwind Directives**: Add the Tailwind directives to your main CSS file (e.g., `src/index.css` or `src/App.css`) in `local-ai-agent`:
        ```css
        @tailwind base;
        @tailwind components;
        @tailwind utilities;
        ```
    *   **Import Google Fonts**: Add the Google Fonts link from `free-cluely-main/index.html` to your `local-ai-agent`'s `index.html` (or equivalent entry point):
        ```html
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
        ```

3.  **Copy Core UI Components and Logic**:
    *   **`App.tsx`**: Copy the `App.tsx` file from `/home/vic/Documents/CODE/free-cluely-main/src/App.tsx` to `local-ai-agent/src/App.tsx` (or your main application component file).
    *   **Pages and Components**: Copy the entire `_pages` and `components` directories from `/home/vic/Documents/CODE/free-cluely-main/src/` to `local-ai-agent/src/`. This includes `Queue.tsx`, `Solutions.tsx`, and all shared UI components (e.g., `ui/toast`, etc.).
    *   **`index.css`**: Copy the `index.css` from `/home/vic/Documents/CODE/free-cluely-main/src/index.css` to `local-ai-agent/src/index.css` (or merge its contents into your main CSS file).
    *   **`main.tsx`**: Review and adapt `main.tsx` from `free-cluely-main` to ensure your `local-ai-agent`'s entry point correctly renders the `App` component and integrates with Electron.

4.  **Install React-specific Dependencies**:
    *   Install `react-query` and `radix-ui` components:
        ```bash
        npm install react-query @radix-ui/react-toast
        # You might need other radix-ui packages depending on what's used in the copied components
        ```

5.  **Replicate Electron IPC (`electronAPI`)**:
    *   The `declare global` block in `App.tsx` defines the `window.electronAPI` interface. You need to implement the corresponding IPC handlers in your `local-ai-agent`'s main Electron process (e.g., in `electron/main.js` or `electron/preload.js`).
    *   **Preload Script**: Create or modify a preload script (e.g., `preload.js`) that exposes the `electronAPI` to the renderer process using Electron's `contextBridge`.
        ```javascript
        // electron/preload.js (example)
        const { contextBridge, ipcRenderer } = require('electron');

        contextBridge.exposeInMainWorld('electronAPI', {
          updateContentDimensions: (dimensions) => ipcRenderer.invoke('update-content-dimensions', dimensions),
          getScreenshots: () => ipcRenderer.invoke('get-screenshots'),
          onUnauthorized: (callback) => ipcRenderer.on('unauthorized', callback),
          // ... expose all other functions defined in the App.tsx electronAPI interface
        });
        ```
    *   **Main Process**: In your main Electron process file (e.g., `electron/main.js`), set up `ipcMain` listeners to handle the calls from the renderer process.
        ```javascript
        // electron/main.js (example)
        const { app, BrowserWindow, ipcMain } = require('electron');
        const path = require('path');

        let mainWindow;

        function createWindow() {
          mainWindow = new BrowserWindow({
            width: 800,
            height: 600,
            webPreferences: {
              preload: path.join(__dirname, 'preload.js'),
              contextIsolation: true,
              nodeIntegration: false,
            },
          });

          mainWindow.loadFile('index.html'); // Or load your React app's build output

          // Handle IPC calls
          ipcMain.handle('update-content-dimensions', (event, dimensions) => {
            // Logic to update window size based on content dimensions
            if (mainWindow) {
              mainWindow.setSize(dimensions.width, dimensions.height);
            }
          });

          // ... implement handlers for all other electronAPI functions
        }

        app.whenReady().then(createWindow);

        app.on('window-all-closed', () => {
          if (process.platform !== 'darwin') {
            app.quit();
          }
        });

        app.on('activate', () => {
          if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
          }
        });
        ```

6.  **Build and Test**:
    *   After copying files and installing dependencies, build your `local-ai-agent` Electron application.
    *   Run the application and thoroughly test the UI to ensure all components render correctly and the Electron IPC works as expected.

By following these steps, you should be able to achieve a near-identical floating window UI in your `local-ai-agent` Electron application.
