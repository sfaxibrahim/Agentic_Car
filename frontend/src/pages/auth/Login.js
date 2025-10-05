// FIXED LoginPage Component
import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { loginUser } from "../../services/api";
import {GoogleLogin} from '@react-oauth/google';
import "../../styles/Auth.css";
import { useLocation } from "react-router-dom";


export default function LoginPage() {
  const navigate = useNavigate();
  const [message, setMessage] = useState({ text: "", type: "" });
  const location = useLocation();
  const [showPassword, setShowPassword] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage({ text: "", type: "" });
    
    try {
      const res = await loginUser(username, password);
      
      if (res.success) {
        // Save tokens in localStorage
        localStorage.setItem("accessToken", res.accessToken);
        localStorage.setItem("refreshToken", res.refreshToken);
        
        navigate("/home", { 
          state: { message: 'Welcome back!', type: 'success' }
        });       
      } else {
        setMessage({ 
          text: res.error || "Login failed", 
          type: 'error' 
        });
      }
    } catch (error) {
      setMessage({ 
        text: "Login failed. Please try again.", 
        type: 'error' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (location.state?.message) {
      setMessage({
        text: location.state.message,
        type: location.state.type || 'success'
      });
      
      // Clear message after 3 seconds
      const timer = setTimeout(() => {
        setMessage({ text: '', type: '' });
      }, 3000);
      
      return () => clearTimeout(timer);
    }
  }, [location.state]);

  return (
    <div className="auth-page">
      <div className="auth-container">
        <h2 className="auth-title">Welcome Back</h2>
        
        <form onSubmit={handleLogin} className="auth-form">
          <div className="input-group">
            <label className="auth-label" htmlFor="username">
              Username
            </label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="auth-input"
              placeholder="Enter your username"
              required
              disabled={isLoading}
            />
          </div>

          <div className="input-group password-group">
            <label className="auth-label" htmlFor="password">
              Password
            </label>
            <div className="password-input-wrapper">
              <input
                type={showPassword ? "text" : "password"}
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="auth-input password-input"
                placeholder="Enter your password"
                required
                disabled={isLoading}
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                disabled={isLoading}
              >
                {showPassword ? '👁️' : '👁️‍🗨️'}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="auth-submit"
            disabled={isLoading}
          >
            {isLoading ? "Signing In..." : "Sign In"}
          </button>
        </form>
        <div className="oauth-login">
          <GoogleLogin
          onSuccess={async (credentialResponse) => {
            try {
              const res = await fetch("http://localhost:8080/api/auth/google", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ token: credentialResponse.credential })
              });
              
              const data = await res.json();
              if (res.ok) {
                localStorage.setItem("accessToken", data.accessToken);
                localStorage.setItem("refreshToken", data.refreshToken);
                navigate("/home", { state: { message: 'Welcome via Google!', type: 'success' } });
              } else {
                alert(data.error || "Google login failed");
              }
            } catch (err) {
              console.error("Google login error", err);
            }
          }}
          onError={() => {
            console.log("Google Login Failed");
          }}
        />
      </div>


        <div className="auth-footer">
          Don't have an account?{" "}
          <Link to="/register" className="auth-link">
            Create Account
          </Link>
        </div>
        
      </div>
      
      {message.text && (
        <div className={`page-message ${message.type}`}>
          {message.text}
          <button 
            className="message-close"
            onClick={() => setMessage({ text: '', type: '' })}
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
}