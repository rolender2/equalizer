const { app, BrowserWindow, screen } = require('electron');
const path = require('path');

let mainWindow;

function createWindow() {
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;

    mainWindow = new BrowserWindow({
        width: width,      // Full screen width
        height: height,    // Full screen height
        x: 0,
        y: 0,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        hasShadow: false,
        skipTaskbar: true,  // Don't show in taskbar
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
        },
    });

    // Enable click-through for transparent areas
    mainWindow.setIgnoreMouseEvents(false);

    // Load Vite Dev Server
    mainWindow.loadURL('http://localhost:5173');

    // Open DevTools (optional for debugging)
    // mainWindow.webContents.openDevTools({ mode: 'detach' });
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
