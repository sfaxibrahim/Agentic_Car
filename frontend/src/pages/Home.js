import React, { useEffect, useState, useRef } from "react";
import "../styles/Home.css";
import {
  fetchUser,
  apiFetch,
  createConversationApi,
  listConversationsApi,
  refreshAccessToken
} from "../services/api";
import { useNavigate } from "react-router-dom";



function Home() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null); // Capital C
  const [userData, setUserData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const lastOpenedConvId = useRef(null);
  
  const navigate = useNavigate();

  const [tokens, setTokens] = useState({
    accessToken: localStorage.getItem("accessToken"),
    refreshToken: localStorage.getItem("refreshToken"),
  });

  const getAccessToken = () => localStorage.getItem("accessToken");

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // --- Token management helpers ---
  const saveTokens = (accessToken, refreshToken) => {
    localStorage.setItem("accessToken", accessToken);
    localStorage.setItem("refreshToken", refreshToken);
    setTokens({ accessToken, refreshToken });
  };

  const handleLogout = () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    setTokens({ accessToken: null, refreshToken: null });
    navigate("/", { replace: true });
  };

  const getFreshAccessToken = async () => {
    let token = tokens.accessToken;
    if (!token) {
      // If token missing, try refresh
      try {
        const newToken = await refreshAccessToken(tokens.refreshToken);
        saveTokens(newToken, tokens.refreshToken);
        token = newToken;
      } catch (err) {
        handleLogout();
        throw new Error("Session expired, please login again.");
      }
    }
    return token;
  };

  const refreshConversations = async () => {
    try {
      const convs = await listConversationsApi();
      setConversations(convs);
      // If there is no active conversation, pick the first one (or null)
      if (!activeConvId && convs.length > 0) {
        await openConversation(convs[0].id);
      }
    } catch (error) {
      console.error("Failed to load conversations", error);
      setConversations([]); 
    }
  };
// -----------------------------
// Delete a conversation
// -----------------------------
const deleteConversation = async (convId) => {
  try {
    await apiFetch(`/conversations/${convId}`, { method: "DELETE" });

    // Get fresh data from server
    const convs = await listConversationsApi();
    setConversations(convs);

    // If we deleted the active conv — open the first remaining or clear UI
    if (activeConvId === convId) {
      lastOpenedConvId.current = null;
      if (convs.length > 0) {
        await openConversation(convs[0].id);
      } else {
        setActiveConvId(null);
        setMessages([]);
      }
    }
  } catch (err) {
    console.error("Failed to delete conversation", err);
    // try to resync anyway
    try {
      const convs = await listConversationsApi();
      setConversations(convs);
    } catch (e) {
      console.error("Failed to refresh conversations after delete error", e);
    }
  }
};


// -----------------------------
// Create a new conversation
// -----------------------------
const handleNewChat = async () => {
  try {
    console.log("🔄 Creating new conversation...");
    const conv = await createConversationApi();
    console.log("✅ Created conversation:", conv);

    // Add new conversation to the list
    setConversations((prev) => [conv, ...prev]);

    // Reset ref before opening
    lastOpenedConvId.current = null;

    // Clear messages and open new conversation
    setMessages([]);
    openConversation(conv.id);
  } catch (err) {
    console.error("❌ Failed to create conversation", err);
  }
};


  // --- In useEffect for conversations ---
  useEffect(() => {
    let didInit = false;

    const loadConversations = async () => {
      try {
        const convs = await listConversationsApi();
        setConversations(convs);

        // Auto-open only once after mount
        if (!didInit && convs.length > 0) {
          didInit = true;
          openConversation(convs[0].id);
        }
      } catch (err) {
        console.error("Failed to load conversations:", err);
        setConversations([]);
      }
    };

    loadConversations();
  }, []); // run only once on mount

  // --- In openConversation ---
  const openConversation = async (convId) => {
  if (!convId || lastOpenedConvId.current === convId) return;
  lastOpenedConvId.current = convId;

  try {
    setLoading(true);
    setActiveConvId(convId);
    
    // Clear existing messages first to prevent duplicates
    setMessages([]);

    const msgs = await apiFetch(`/conversations/${convId}/messages`, {
      method: "GET",
    });

    const normalized = msgs.map((m) => ({
      id: m.id,
      type: m.role === "USER" ? "user" : "ai",
      content: m.content,
      timestamp: m.createdAt,
      file: null,
    }));

    setMessages(normalized);
    setTimeout(scrollToBottom, 50);
  } catch (error) {
    console.error("Failed to open conversation", error);
  } finally {
    setLoading(false);
  }
};


  useEffect(() => {
    const loadUser = async () => {
      try {
        const data = await fetchUser();
        setUserData(data);
      } catch (err) {
        setError("Failed to load user");
        console.error(err);
      }
    };

    loadUser();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    document.body.classList.toggle("dark-mode", darkMode);
  }, [darkMode]);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
    }
  }, [question]);

  const playNotificationSound = () => {
    // Create a subtle notification sound
    const audioContext = new (window.AudioContext ||
      window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
    oscillator.frequency.setValueAtTime(600, audioContext.currentTime + 0.1);

    gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(
      0.01,
      audioContext.currentTime + 0.2
    );

    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.2);
  };

 
    const renderMessageContent = (message) => {
    const content = message.content;

    // ===== CHECK 1: Is it a CAR LISTING? =====
    if (content.includes('**Option') && (content.includes('BMW') || content.includes('Price:'))) {
      return renderCarListings(content);  // Use the car cards function
    }

    // ===== CHECK 2: Is it a VIDEO LISTING? =====
    if (content.includes('[VIDEO_EMBED]')) {
      // Your EXISTING video code stays here - don't change it
      const cleanContent = content.replace(/\\n/g, "\n");
      const parts = cleanContent.split(/Video \d+:/);
      const introText = parts[0].trim();
      const videoSections = parts.slice(1);

      return (
        <div className="message-text">
          <div style={{ marginBottom: "20px", fontSize: "16px", whiteSpace: "pre-wrap" }}>
            {introText}
          </div>

          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
            gap: "20px",
          }}>
            {videoSections.map((section, idx) => {
              const embedMatch = section.match(/\[VIDEO_EMBED\](.*?)\[\/VIDEO_EMBED\]/);
              const embedUrl = embedMatch ? embedMatch[1] : null;
              const textContent = section.replace(/\[VIDEO_EMBED\].*?\[\/VIDEO_EMBED\]/, "").trim();
              const lines = textContent.split("\n").filter((line) => line.trim());
              const title = lines[0] || `Video ${idx + 1}`;
              const channel = lines.find((line) => line.includes("Channel:")) || "";

              return (
                <div key={idx} style={{
                  border: "1px solid #ddd",
                  borderRadius: "12px",
                  overflow: "hidden",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
                }}>
                  {embedUrl && (
                    <div style={{ position: "relative", paddingBottom: "56.25%", height: 0 }}>
                      <iframe
                        src={embedUrl}
                        style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%" }}
                        frameBorder="0"
                        allowFullScreen
                      />
                    </div>
                  )}
                  <div style={{ padding: "16px" }}>
                    <h3 style={{ margin: "0 0 8px 0", fontSize: "16px" }}>{title}</h3>
                    {channel && <p style={{ margin: 0, fontSize: "14px", color: "#666" }}>{channel}</p>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      );
    }

    // ===== CHECK 3: Default - Regular text =====
    return (
      <div className="message-text" style={{ whiteSpace: "pre-wrap" }}>
        {content}
      </div>
    );
  };
  
const renderCarListings = (content) => {
  if (!content.includes('**Option') || !content.includes('Price:')) {
    return content;
  }

  const parts = content.split(/\*\*Option \d+:\*\*/);
  const introText = parts[0].trim();
  const carSections = parts.slice(1);

  return (
    <div className="message-text">
      {introText && (
        <div style={{ marginBottom: '1.25rem', fontSize: '0.9375rem', color: darkMode ? '#e0e0e0' : '#333' }}>
          {introText}
        </div>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 18rem), 1fr))',
          gap: '1rem',
        }}
      >
        {carSections.map((section, idx) => {
            const lines = section.split('\n').filter(l => l.trim());

    // Find the title line
          const titleLine = lines.find(l =>
              l.trim().startsWith('•') &&
              !l.includes('Price:') &&
              !l.includes('Year:') &&
              !l.includes('Mileage:') &&
              !l.includes('Fuel:') &&
              !l.includes('Transmission:') &&
              !l.includes('Location:') &&
              !l.includes('Link:')
          );
          const title = titleLine ? titleLine.replace(/•/g, '').trim() : '';

          const price = lines.find(l => l.includes('Price:'))?.split('Price:')[1]?.trim() || 'N/A';
          const year = lines.find(l => l.includes('Year:'))?.split('Year:')[1]?.trim() || 'N/A';
          const mileage = lines.find(l => l.includes('Mileage:'))?.split('Mileage:')[1]?.trim() || 'N/A';
          const fuel = lines.find(l => l.includes('Fuel:'))?.split('Fuel:')[1]?.trim() || 'N/A';
          const transmission = lines.find(l => l.includes('Transmission:'))?.split('Transmission:')[1]?.trim() || 'N/A';
          const location = lines.find(l => l.includes('Location:'))?.split('Location:')[1]?.trim() || 'N/A';
          let link = null;
          const linkLine = lines.find(l => l.includes('Link:'));
          if (linkLine) {
            // Extract URL inside parentheses if Markdown-style
            const match = linkLine.match(/\((https?:\/\/[^\s)]+)\)/);
            if (match) {
              link = match[1]; // correct URL
            } else {
              // fallback: just remove 'Link:' and trim
              link = linkLine.split('Link:')[1].replace(/[\[\]]/g, '').trim();
            }
          }

          return (
            <div
              key={idx}
              style={{
                border: darkMode ? '1px solid #333' : '1px solid #e5e5e5',
                borderRadius: '0.5rem',
                overflow: 'hidden',
                backgroundColor: darkMode ? '#1a1a1a' : '#ffffff',
                transition: 'all 0.2s ease',
                cursor: 'pointer',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#3b82f6';
                e.currentTarget.style.boxShadow = '0 0.25rem 0.75rem rgba(59, 130, 246, 0.15)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = darkMode ? '#333' : '#e5e5e5';
                e.currentTarget.style.boxShadow = 'none';
              }}
              onClick={() => link && window.open(link, '_blank')}
            >
              {/* Header */}
              <div
                style={{
                  padding: '1rem 1.25rem',
                  borderBottom: darkMode ? '1px solid #333' : '1px solid #f0f0f0',
                  backgroundColor: darkMode ? '#0f0f0f' : '#fafafa',
                }}
              >
                <h3
                  style={{
                    margin: 0,
                    fontSize: '0.9375rem',
                    fontWeight: '600',
                    color: darkMode ? '#fff' : '#1a1a1a',
                    lineHeight: '1.5',
                  }}
                >
                  {title || 'Vehicle'}
                </h3>
              </div>

              {/* Body */}
              <div style={{ padding: '1.25rem' }}>
                {/* Price */}
                {price && (
                  <div
                    style={{
                      fontSize: '1.5rem',
                      fontWeight: '700',
                      color: '#3b82f6',
                      marginBottom: '1rem',
                      letterSpacing: '-0.02em',
                    }}
                  >
                    {price}
                  </div>
                )}

                {/* Specs */}
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.625rem',
                    fontSize: '0.875rem',
                  }}
                >
                  {year && (
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: darkMode ? '#888' : '#666', fontWeight: '500' }}>Year</span>
                      <span style={{ color: darkMode ? '#e0e0e0' : '#1a1a1a', fontWeight: '600' }}>{year}</span>
                    </div>
                  )}
                  {mileage && (
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: darkMode ? '#888' : '#666', fontWeight: '500' }}>Mileage</span>
                      <span style={{ color: darkMode ? '#e0e0e0' : '#1a1a1a', fontWeight: '600' }}>{mileage}</span>
                    </div>
                  )}
                  {/* {fuel && (
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: darkMode ? '#888' : '#666', fontWeight: '500' }}>Fuel</span>
                      <span style={{ color: darkMode ? '#e0e0e0' : '#1a1a1a', fontWeight: '600' }}>{fuel}</span>
                    </div>
                  )} */}
                  {transmission && (
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: darkMode ? '#888' : '#666', fontWeight: '500' }}>Transmission</span>
                      <span style={{ color: darkMode ? '#e0e0e0' : '#1a1a1a', fontWeight: '600' }}>{transmission}</span>
                    </div>
                  )}
                </div>

                {/* Location */}
                {location && (
                  <div
                    style={{
                      marginTop: '1rem',
                      paddingTop: '1rem',
                      borderTop: darkMode ? '1px solid #2a2a2a' : '1px solid #f0f0f0',
                      fontSize: '0.8125rem',
                      color: darkMode ? '#888' : '#666',
                    }}
                  >
                    {location}
                  </div>
                )}

                {/* Button */}
                {link && (
                  <button
                    style={{
                      marginTop: '1rem',
                      width: '100%',
                      padding: '0.75rem',
                      backgroundColor: darkMode ? '#fff' : '#1a1a1a',
                      color: darkMode ? '#1a1a1a' : '#fff',
                      border: 'none',
                      borderRadius: '0.375rem',
                      fontSize: '0.875rem',
                      fontWeight: '600',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = '#3b82f6';
                      e.currentTarget.style.color = '#fff';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = darkMode ? '#fff' : '#1a1a1a';
                      e.currentTarget.style.color = darkMode ? '#1a1a1a' : '#fff';
                    }}
                  >
                    View Details
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
  
  const askAIStream = async () => {
    if ((!question.trim() && !uploadedFile) || loading) return;

    const currentQuestion = question.trim();
    const currentFile = uploadedFile;

    setQuestion("");
    setUploadedFile(null);
    setLoading(true);

    let content = currentQuestion;
    if (currentFile) content += `\n[File: ${currentFile.name}]`;

    // Add user message locally (no waiting for server)
    const userMessageId = `local-user-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      {
        id: userMessageId,
        type: "user",
        content: content,
        timestamp: new Date(),
      },
    ]);

    try {
      const accessToken = await getFreshAccessToken();
      const response = await fetch(`${process.env.REACT_APP_FASTAPI_URL}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          question: currentQuestion,
          convId: activeConvId,
        }),
      });

      if (!response.ok) {
        throw new Error(`Stream failed: ${response.status}`);
      }

      // Add temporary AI message
      const aiMessageId = `local-ai-${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        { id: aiMessageId, type: "ai", content: "", timestamp: new Date() },
      ]);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        if (!chunk) continue;

        fullText += chunk;

        // Update AI message progressively
        setMessages((prev) =>
          prev.map((m) =>
            m.id === aiMessageId ? { ...m, content: fullText } : m
          )
        );
      }

      playNotificationSound();

      // 🔑 After stream finished, sync from server (once!)
      await openConversation(activeConvId);

    } catch (err) {
      console.error("Error:", err);
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          type: "ai",
          content: `⚠️ Error: ${err.message}`,
          timestamp: new Date(),
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };


  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      askAIStream();
    }
  };

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file && file.size <= 10 * 1024 * 1024) {
      // 10MB limit
      setUploadedFile(file);
    } else {
      alert("File size should be less than 10MB");
    }
  };

  const removeFile = () => {
    setUploadedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const exportChat = () => {
    const chatData = {
      exportDate: new Date().toISOString(),
      messageCount: messages.length,
      messages: messages.map((msg) => ({
        type: msg.type,
        content: msg.content,
        timestamp: msg.timestamp.toISOString(),
        reactions: msg.reactions,
      })),
    };

    const blob = new Blob([JSON.stringify(chatData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `chat-export-${new Date().toISOString().split("T")[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className={`app ${darkMode ? "dark" : ""}`}>
      <div className="chat-container">
        {/* Enhanced Sidebar */}
        <div className="sidebar">
          <div className="sidebar-header">
            <div className="header-main">
              <h2>AutoSense AI</h2>
              <span className="version">v2.0 Pro</span>
            </div>
            <div className="header-icons">
              <button
                onClick={toggleDarkMode}
                className="icon-btn"
                title="Toggle Theme"
              >
                {darkMode ? (
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                  >
                    <circle cx="12" cy="12" r="5" />
                    <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
                  </svg>
                ) : (
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                  >
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                  </svg>
                )}
              </button>

              <button
                onClick={exportChat}
                className="icon-btn"
                disabled={messages.length === 0}
                title="Export Chat"
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                >
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7,10 12,15 17,10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
              </button>
            </div>
          </div>

          <div className="sidebar-controls">
            <button
              onClick={handleNewChat}
              className="control-btn new-chat"
              title="New Chat"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14,2 14,8 20,8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10,9 9,9 8,9" />
              </svg>
              New Chat
            </button>
          </div>
          
          <div className="conversations-list">
            {conversations.map(c => (
              <div
                key={c.id}
                className={`conv-item ${c.id === activeConvId ? "active" : ""}`}
                onClick={() => openConversation(c.id)}
              >
                <div className="conv-content">
                  <div className="conv-title">{c.title || "New conversation"}</div>
                  <div className="conv-meta">{c.updatedAt ? new Date(c.updatedAt).toLocaleString() : ""}</div>
                </div>
                <button 
                  className="conv-delete"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteConversation(c.id);
                  }}
                  title="Delete conversation"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <polyline points="3,6 5,6 21,6"></polyline>
                    <path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2V6"></path>
                    <line x1="10" y1="11" x2="10" y2="17"></line>
                    <line x1="14" y1="11" x2="14" y2="17"></line>
                  </svg>
                </button>
              </div>
            ))}
          </div>

          <div className="chat-info">
          
            <div className="info-item">
              <span className="label">Messages:</span>
              <span className="value">{messages.length}</span>
            </div>

            <div className="info-item">
              <span className="label">Status:</span>
              <span className={`status ${loading ? "busy" : "ready"}`}>
                {loading ? "Processing..." : "Ready"}
              </span>
            </div>
            <div className="info-item">
              <span className="label">Welcome :</span>
              <span className="value">
                {userData ? userData.username : "Loading......"}
              </span>
              <button
                onClick={handleLogout}
                className="logout-btn"
                title="Logout"
              >
                <svg
                  className="logout-icon"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                >
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16,17 21,12 16,7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="main-chat">
          {/* Messages */}
          <div className="messages-area">
            {messages.length === 0 ? (
              <div className="welcome-screen">
                <div className="welcome-icon">🚗</div>
                <h1>Welcome to AutoSense AI</h1>
                <p>
                  Your intelligent automotive assistant with video tutorials and
                  real-time information!
                </p>

                <div className="welcome-suggestions">
                  <button
                    onClick={() => setQuestion("Show me .... videos")}
                    className="suggestion-chip"
                  >
                    Cars Videos
                  </button>
                  <button
                    onClick={() => setQuestion("current .... price ")}
                    className="suggestion-chip"
                  >
                    Current Research
                  </button>
                  <button
                    onClick={() => setQuestion("Engine maintenance checklist")}
                    className="suggestion-chip"
                  >
                    Maintenance Tips
                  </button>
                </div>
              </div>
            ) : (
              <div className="messages-list">
                {messages.map((message) => (
                  <div key={message.id} className={`message ${message.type}`}>
                    <div className="message-avatar">
                      <div className={`${message.type}-avatar`}>
                        {message.type === "user" ? "👤" : "⌬"}
                      </div>
                    </div>
                    <div className="message-content">
                      <div
                        className={`message-bubble ${message.type} ${
                          message.isError ? "error" : ""
                        }`}
                      >
                        {renderMessageContent(message)}
                        {message.file && (
                          <div className="file-attachment">
                            <div className="file-icon">📁</div>
                            <span className="file-name">
                              {message.file.name}
                            </span>
                            <span className="file-size">
                              ({(message.file.size / 1024).toFixed(1)}KB)
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="message ai">
                    <div className="message-avatar">
                      <div className="ai-avatar">⌬</div>
                    </div>
                    <div className="message-content">
                      <div className="message-bubble ai typing">
                        <div className="typing-dots">
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Enhanced Input Area */}
          <div className="input-area">
            {/* File Upload Preview */}
            {uploadedFile && (
              <div className="file-preview">
                <div className="file-info">
                  <div className="file-icon">📁</div>
                  <span className="file-name">{uploadedFile.name}</span>
                  <span className="file-size">
                    ({(uploadedFile.size / 1024).toFixed(1)}KB)
                  </span>
                </div>
                <button onClick={removeFile} className="remove-file">
                  ×
                </button>
              </div>
            )}

            <div className="input-container">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="attachment-btn"
                title="Upload File"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                >
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                </svg>
              </button>

              <textarea
                ref={textareaRef}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about cars, request videos, or get current prices..."
                disabled={loading}
                className="message-input"
                rows="1"
              />

              <button
                onClick={askAIStream}
                disabled={loading || (!question.trim() && !uploadedFile)}
                className="send-button"
                title="Send message"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                >
                  <path d="M22 2L11 13" />
                  <path d="M22 2L15 22L11 13L2 9L22 2z" />
                </svg>
              </button>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileUpload}
              style={{ display: "none" }}
              accept="*/*"
            />

            <div className="input-footer">
              <span className="input-hint">
                Press Enter to send • Shift+Enter for new line • Videos embedded
                automatically
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Home;