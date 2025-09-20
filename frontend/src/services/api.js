// FIXED API Service - api.js
const BASE_URL = "http://localhost:8080/api";

export async function registerUser(username, email, password) {
  try {
    const response = await fetch(`${BASE_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      // Success - backend returns a success message string
      return { success: true, message: data };
    } else {
      // Error - backend returns error message
      return { success: false, error: data };
    }
  } catch (error) {
    return { success: false, error: "Network error occurred" };
  }
}

export async function loginUser(username, password) {
  try {
    const response = await fetch(`${BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      // Success - backend returns JwtResponse with accessToken and refreshToken
      return { 
        success: true, 
        accessToken: data.accessToken, 
        refreshToken: data.refreshToken 
      };
    } else {
      // Error - backend returns error message string
      return { success: false, error: data };
    }
  } catch (error) {
    return { success: false, error: "Network error occurred" };
  }
}


function getTokens(){
  return {
    accessToken: localStorage.getItem("accessToken"),
    refreshToken: localStorage.getItem("refreshToken")
  };
}
// Save tokens to localStorage
function setTokens({ accessToken, refreshToken }) {
  localStorage.setItem("accessToken", accessToken);
  localStorage.setItem("refreshToken", refreshToken);
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
    throw new Error("Refresh token expired or invalid");
  }
  const data = await response.json();
  setTokens({ accessToken: data.accessToken, refreshToken: data.refreshToken });
  return data.accessToken;
}

// services/api.js
export async function fetchUser() {
  try {
    const data = await apiFetch("/user/me");
    return data;
  } catch (err) {
    console.error("Failed to fetch user:", err);
    throw err; // propagate to component
  }
}



// Generic fetch wrapper that auto-refreshes token
export async function apiFetch(url, options = {}) {
  let { accessToken } = getTokens();

  // Add Authorization header
  options.headers = {
    ...options.headers,
    "Content-Type": "application/json",
    Authorization: `Bearer ${accessToken}`,
  };

  let response = await fetch(`${BASE_URL}${url}`, options);

  // If token expired, refresh and retry
  if (response.status === 401) {
    try {
      accessToken = await refreshAccessToken(); // refresh
      options.headers.Authorization = `Bearer ${accessToken}`;
      response = await fetch(`${BASE_URL}${url}`, options); // retry
    } catch (err) {
      throw new Error("Session expired. Please login again.");
    }
  }

  const data = await response.json();
  if (!response.ok) throw new Error(data);
  return data;
}
