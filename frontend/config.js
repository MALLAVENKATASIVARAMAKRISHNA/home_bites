const IS_LOCAL_HOST =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1" ||
  window.location.hostname === "";

window.API_BASE_URL =
  window.HOME_BITES_API_BASE_URL ||
  (IS_LOCAL_HOST ? "http://127.0.0.1:8000" : "https://home-bites.onrender.com");
