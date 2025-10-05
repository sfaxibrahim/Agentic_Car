// =====================
// Robust API Service - api.js
// =====================

const BASE_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8080/api";



// ---------------------
// TOKEN STORAGE HELPERS
// ---------------------
function getTokens() {
  return {
    accessToken: localStorage.getItem("accessToken"),
    refreshToken: localStorage.getItem("refreshToken"),
  };
}

function setTokens({ accessToken, refreshToken }) {
  if (accessToken) localStorage.setItem("accessToken", accessToken);
  if (refreshToken) localStorage.setItem("refreshToken", refreshToken);
}

function clearTokens() {
  localStorage.removeItem("accessToken");
  localStorage.removeItem("refreshToken");
}

// ---------------------
// AUTH FUNCTIONS
// ---------------------
export async function registerUser(username, email, password) {
  try {
    const response = await fetch(`${BASE_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password }),
    });

    const data = await response.json();
    return response.ok
      ? { success: true, message: data }
      : { success: false, error: data };
  } catch {
    return { success: false, error: "Network error occurred" };
  }
}

export async function loginUser(username, password) {
  try {
    const response = await fetch(`${BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    const data = await response.json();

    if (response.ok) {
      setTokens({ accessToken: data.accessToken, refreshToken: data.refreshToken });
      return { success: true, accessToken: data.accessToken, refreshToken: data.refreshToken };
    } else {
      return { success: false, error: data };
    }
  } catch {
    return { success: false, error: "Network error occurred" };
  }
}

export async function refreshAccessToken() {
  const { refreshToken } = getTokens();
  if (!refreshToken) throw new Error("No refresh token available");

  const response = await fetch(`${BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refreshToken }),
  });

  if (!response.ok) {
    clearTokens();
    throw new Error("Refresh token expired or invalid");
  }

  const data = await response.json();
  setTokens({ accessToken: data.accessToken, refreshToken: data.refreshToken });
  return data.accessToken;
}

// ---------------------
// MAIN FETCH WRAPPER
// ---------------------
export const apiFetch = async (endpoint, options = {}) => {
  let { accessToken } = getTokens(); // always fresh

  
  const makeRequest = async (token) => {
    return fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
  };

  let response = await makeRequest(accessToken);

  if (response.status === 401 || response.status === 403) {
    try {
      console.log("[apiFetch] Access token expired, refreshing...");
      accessToken = await refreshAccessToken(); // refresh and update local var

      response = await makeRequest(accessToken); // retry with new token
      console.log("[apiFetch] Retried request status:", response.status);
    } catch (err) {
      console.error("[apiFetch] Refresh failed:", err);
      clearTokens();
      throw new Error("Session expired. Please log in again.");
    }
  }

  if (!response.ok) throw new Error(`API request failed: ${response.status} ${response.statusText}`);

  return response.json();
};

// ---------------------
// USER API
// ---------------------
export async function fetchUser() {
  try {
    return await apiFetch("/user/me");
  } catch (err) {
    console.error("[fetchUser] Failed:", err);
    throw err;
  }
}

// ---------------------
// CONVERSATION APIs
// ---------------------
export const listConversationsApi = () => apiFetch("/conversations", { method: "GET" });

export async function createConversationApi() {
  return await apiFetch("/conversations", { method: "POST"});
}


