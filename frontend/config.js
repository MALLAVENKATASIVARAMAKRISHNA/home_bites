const API_BASE_URL =
  window.HOME_BITES_API_BASE_URL ||
  (window.location.protocol.startsWith("http") ? `${window.location.origin}` : "http://127.0.0.1:8000");
