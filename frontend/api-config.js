window.__APP_CONFIG__ = window.__APP_CONFIG__ || {};
const defaultHost = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  ? "http://127.0.0.1:5000"
  : "https://YOUR_RENDER_BACKEND.onrender.com";

window.__APP_CONFIG__.API_BASE = window.__APP_CONFIG__.API_BASE || defaultHost;
window.__APP_CONFIG__.API_BASE = window.__APP_CONFIG__.API_BASE.replace(/\/$/, "");
// Replace YOUR_RENDER_BACKEND.onrender.com with your actual Render URL after deployment.
