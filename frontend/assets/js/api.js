/**
 * Thin fetch wrapper for the BT Real Estate API.
 * Handles JWT storage, attaching the Authorization header, transparently
 * refreshing an expired access token once, and unwrapping the backend's
 * standard {success, message, data, errors} response envelope.
 */
(function () {
  const TOKENS_KEY = "bt_auth_tokens";

  function getTokens() {
    try {
      return JSON.parse(localStorage.getItem(TOKENS_KEY)) || null;
    } catch (e) {
      return null;
    }
  }

  function setTokens(tokens) {
    localStorage.setItem(TOKENS_KEY, JSON.stringify(tokens));
  }

  function clearTokens() {
    localStorage.removeItem(TOKENS_KEY);
  }

  function isLoggedIn() {
    const tokens = getTokens();
    return !!(tokens && tokens.access);
  }

  async function refreshAccessToken() {
    const tokens = getTokens();
    if (!tokens || !tokens.refresh) return null;

    try {
      const res = await fetch(`${window.API_BASE_URL}/auth/refresh/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: tokens.refresh }),
      });
      const payload = await res.json().catch(() => null);
      if (!res.ok || !payload || !payload.data) {
        clearTokens();
        return null;
      }
      const newTokens = {
        access: payload.data.access,
        refresh: payload.data.refresh || tokens.refresh,
      };
      setTokens(newTokens);
      return newTokens.access;
    } catch (e) {
      return null;
    }
  }

  /**
   * @param {string} path - e.g. "/listings/" (appended to API_BASE_URL)
   * @param {object} options
   *   method: "GET"|"POST"|"PATCH"|"PUT"|"DELETE"
   *   body: plain object (JSON) or FormData (for file uploads)
   *   auth: whether to attach the Authorization header if a token exists (default true)
   */
  async function apiRequest(path, options = {}) {
    const { method = "GET", body = null, auth = true } = options;
    const isFormData = typeof FormData !== "undefined" && body instanceof FormData;

    async function doFetch(retryOn401) {
      const tokens = getTokens();
      const headers = {};
      if (!isFormData && body !== null) headers["Content-Type"] = "application/json";
      if (auth && tokens && tokens.access) headers["Authorization"] = `Bearer ${tokens.access}`;

      const res = await fetch(`${window.API_BASE_URL}${path}`, {
        method,
        headers,
        body: body === null ? undefined : isFormData ? body : JSON.stringify(body),
      });

      let payload = null;
      try {
        payload = await res.json();
      } catch (e) {
        payload = null;
      }

      if (res.status === 401 && auth && retryOn401 && tokens && tokens.refresh) {
        const newAccess = await refreshAccessToken();
        if (newAccess) return doFetch(false);
      }

      if (!res.ok) {
        const message = (payload && payload.message) || "Something went wrong. Please try again.";
        const error = new Error(message);
        error.status = res.status;
        error.errors = payload && payload.errors;
        throw error;
      }

      return payload ? payload.data : null;
    }

    return doFetch(true);
  }

  window.BTApi = {
    get: (path, options) => apiRequest(path, { ...options, method: "GET" }),
    post: (path, body, options) => apiRequest(path, { ...options, method: "POST", body }),
    patch: (path, body, options) => apiRequest(path, { ...options, method: "PATCH", body }),
    delete: (path, options) => apiRequest(path, { ...options, method: "DELETE" }),
    getTokens,
    setTokens,
    clearTokens,
    isLoggedIn,
  };
})();
