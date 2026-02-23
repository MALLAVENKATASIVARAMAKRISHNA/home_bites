function setAlert(el, type, text) {
  el.textContent = text;
  el.className = `alert ${type} show`;
}

function clearAlert(el) {
  el.textContent = "";
  el.className = "alert";
}

function setButtonLoading(button, loadingText, isLoading) {
  if (!button.dataset.defaultText) {
    button.dataset.defaultText = button.textContent;
  }
  button.disabled = isLoading;
  button.textContent = isLoading ? loadingText : button.dataset.defaultText;
}

function setupPasswordToggle(inputId, toggleId) {
  const input = document.getElementById(inputId);
  const toggle = document.getElementById(toggleId);
  if (!input || !toggle) return;

  toggle.addEventListener("click", () => {
    const hidden = input.type === "password";
    input.type = hidden ? "text" : "password";
    toggle.textContent = hidden ? "Hide" : "Show";
  });
}

function clearStoredAuth() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user");
}

function decodeJwtPayload(token) {
  try {
    const parts = String(token || "").split(".");
    if (parts.length < 2) return null;
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
    return JSON.parse(atob(padded));
  } catch (err) {
    return null;
  }
}

function getTokenExpiryMs(token) {
  const payload = decodeJwtPayload(token);
  const expSeconds = Number(payload?.exp);
  if (!Number.isFinite(expSeconds) || expSeconds <= 0) return null;
  return expSeconds * 1000;
}

function getValidAccessToken() {
  const token = localStorage.getItem("access_token");
  if (!token) return null;
  const expiryMs = getTokenExpiryMs(token);
  if (!expiryMs || expiryMs <= Date.now()) {
    clearStoredAuth();
    return null;
  }
  return token;
}

function stopSessionExpiryWatcher() {
  if (window.__homeBitesSessionExpiryTimer) {
    clearTimeout(window.__homeBitesSessionExpiryTimer);
    window.__homeBitesSessionExpiryTimer = null;
  }
}

function startSessionExpiryWatcher(onExpire) {
  stopSessionExpiryWatcher();
  const token = localStorage.getItem("access_token");
  if (!token) return;

  const expiryMs = getTokenExpiryMs(token);
  if (!expiryMs) {
    clearStoredAuth();
    if (typeof onExpire === "function") onExpire();
    return;
  }

  const remainingMs = expiryMs - Date.now();
  if (remainingMs <= 0) {
    clearStoredAuth();
    if (typeof onExpire === "function") onExpire();
    return;
  }

  window.__homeBitesSessionExpiryTimer = setTimeout(() => {
    clearStoredAuth();
    if (typeof onExpire === "function") onExpire();
  }, remainingMs + 200);
}
