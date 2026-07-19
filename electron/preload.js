/**
 * Preload script: exposes a minimal API to the renderer when contextIsolation is true.
 * Only window-minimize, window-maximize, window-close and openExternal are exposed.
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('atlasBridge', {
  send: (channel, ...args) => {
    const allowed = ['window-minimize', 'window-maximize', 'window-close'];
    if (allowed.includes(channel)) {
      ipcRenderer.send(channel, ...args);
    }
  },
  openExternal: (url) => {
    // Renderer will call atlasBridge.openExternal(url); main listens and calls shell.openExternal
    ipcRenderer.send('open-external', url);
  },
});
