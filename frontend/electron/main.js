const { app, BrowserWindow, screen, globalShortcut, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');

let mainWindow;

// Path to store window position
const configPath = path.join(app.getPath('userData'), 'window-position.json');

function loadPosition() {
    try {
        if (fs.existsSync(configPath)) {
            const data = fs.readFileSync(configPath, 'utf8');
            return JSON.parse(data);
        }
    } catch (err) {
        console.error('Error loading position:', err);
    }
    return null;
}

function savePosition(bounds) {
    try {
        fs.writeFileSync(configPath, JSON.stringify(bounds));
    } catch (err) {
        console.error('Error saving position:', err);
    }
}

function createWindow() {
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;
    const savedPosition = loadPosition();

    mainWindow = new BrowserWindow({
        width: width,
        height: height,
        x: savedPosition?.x ?? 0,
        y: savedPosition?.y ?? 0,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        hasShadow: false,
        skipTaskbar: true,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
        },
    });

    mainWindow.setIgnoreMouseEvents(false);
    mainWindow.loadURL('http://localhost:5173');

    // Aggressive always-on-top handling for Linux
    const forceOnTop = () => {
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.setAlwaysOnTop(true, 'floating');
            mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
        }
    };

    // Apply immediately
    forceOnTop();

    // Re-apply after load
    mainWindow.webContents.on('did-finish-load', forceOnTop);

    // Re-apply when shown
    mainWindow.on('show', forceOnTop);

    // Re-apply on focus
    mainWindow.on('focus', forceOnTop);

    // Periodic re-apply for stubborn window managers (every 2 seconds for first 10 seconds)
    let attempts = 0;
    const interval = setInterval(() => {
        forceOnTop();
        attempts++;
        if (attempts >= 5) clearInterval(interval);
    }, 2000);

    // Save position when window moves
    mainWindow.on('moved', () => {
        const bounds = mainWindow.getBounds();
        savePosition({ x: bounds.x, y: bounds.y });
        console.log(`Position saved: ${bounds.x}, ${bounds.y}`);
    });

    // Register global shortcut: Ctrl+Shift+S to toggle listening
    globalShortcut.register('CommandOrControl+Shift+S', () => {
        console.log('Toggle shortcut pressed');
        mainWindow.webContents.send('toggle-listening');
    });
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

app.on('will-quit', () => {
    globalShortcut.unregisterAll();
});
