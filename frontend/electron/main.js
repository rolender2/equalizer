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

    // Ensure always on top works on Linux
    mainWindow.setAlwaysOnTop(true, 'screen-saver');

    // Focus the window after a short delay to bring it to front
    setTimeout(() => {
        mainWindow.setAlwaysOnTop(true, 'screen-saver');
        mainWindow.focus();
    }, 1000);

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
