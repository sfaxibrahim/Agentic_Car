import React, { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    document.body.classList.toggle('dark-mode', darkMode);
  }, [darkMode]);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
  }, [question]);

  const playNotificationSound = () => {
    // Create a subtle notification sound
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
    oscillator.frequency.setValueAtTime(600, audioContext.currentTime + 0.1);
    
    gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.2);
  };

  const askAI = async () => {
    if ((!question.trim() && !uploadedFile) || loading) return;
    
    let content = question.trim();
    if (uploadedFile) {
      content += uploadedFile ? `\n[File: ${uploadedFile.name}]` : '';
    }

    const userMessage = { 
      id: Date.now(), 
      type: 'user', 
      content: content,
      file: uploadedFile,
      timestamp: new Date(),
      reactions: {}
    };
    setMessages(prev => [...prev, userMessage]);
    
    const currentQuestion = question.trim();
    setQuestion('');
    setUploadedFile(null);
    setLoading(true);
    
    // Play send sound
    playNotificationSound();
    
    try {
      const response = await fetch('http://localhost:8080/api/chat', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question: currentQuestion })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.text();
      const aiMessage = { 
        id: Date.now() + 1, 
        type: 'ai', 
        content: data, 
        timestamp: new Date(),
        reactions: {}
      };
      setMessages(prev => [...prev, aiMessage]);
      
      // Play receive sound
      setTimeout(() => playNotificationSound(), 100);
    } catch (err) {
      console.error('Error:', err);
      const errorMessage = { 
        id: Date.now() + 1, 
        type: 'ai', 
        content: `Sorry, I encountered an error: ${err.message}`, 
        timestamp: new Date(), 
        isError: true,
        reactions: {}
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      askAI();
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  const formatTime = (date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file && file.size <= 10 * 1024 * 1024) { // 10MB limit
      setUploadedFile(file);
    } else {
      alert('File size should be less than 10MB');
    }
  };

  const removeFile = () => {
    setUploadedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const exportChat = () => {
    const chatData = {
      exportDate: new Date().toISOString(),
      messageCount: messages.length,
      messages: messages.map(msg => ({
        type: msg.type,
        content: msg.content,
        timestamp: msg.timestamp.toISOString(),
        reactions: msg.reactions
      }))
    };
    
    const blob = new Blob([JSON.stringify(chatData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-export-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className={`app ${darkMode ? 'dark' : ''}`}>
      <div className="chat-container">
        {/* Enhanced Sidebar */}
        <div className="sidebar">
          <div className="sidebar-header">
            <div className="header-main">
              <h2>AI Assistant</h2>
              <span className="version">v2.0 Pro</span>
            </div>
            <div className="header-icons">
              <button 
                onClick={toggleDarkMode}
                className="icon-btn"
                title="Toggle Theme"
              >
                {darkMode ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <circle cx="12" cy="12" r="5"/>
                    <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
                  </svg>
                ) : (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                  </svg>
                )}
              </button>

              <button 
                onClick={exportChat}
                className="icon-btn"
                disabled={messages.length === 0}
                title="Export Chat"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="7,10 12,15 17,10"/>
                  <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
              </button>
            </div>
          </div>
          
          <div className="sidebar-controls">
            <button 
              onClick={clearChat} 
              className="control-btn new-chat"
              disabled={messages.length === 0}
              title="New Chat"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14,2 14,8 20,8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10,9 9,9 8,9"/>
              </svg>
              New Chat
            </button>
          </div>

          <div className="chat-info">
            <div className="info-item">
              <span className="label">Messages:</span>
              <span className="value">{messages.length}</span>
            </div>
           
            <div className="info-item">
              <span className="label">Status:</span>
              <span className={`status ${loading ? 'busy' : 'ready'}`}>
                {loading ? 'Thinking...' : 'Ready'}
              </span>
            </div>
            <div className="info-item">
              <span className="label">Theme:</span>
              <span className="value">{darkMode ? 'Dark' : 'Light'}</span>
            </div>
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="main-chat">
          {/* Messages */}
          <div className="messages-area">
            {messages.length === 0 ? (
              <div className="welcome-screen">
                <div className="welcome-icon">🤖</div>
                <h1>Welcome to AutoSense AI</h1>
                <p>Enhanced with reactions, file uploads, search, and more!</p>
               
                <div className="welcome-suggestions">
                  <button 
                    onClick={() => setQuestion("What are your new features?")}
                    className="suggestion-chip"
                  >
                    What are your new features?
                  </button>
                  <button 
                    onClick={() => setQuestion("Tell me about file uploads")}
                    className="suggestion-chip"
                  >
                    Tell me about file uploads
                  </button>
                  <button 
                    onClick={() => setQuestion("How do reactions work?")}
                    className="suggestion-chip"
                  >
                    How do reactions work?
                  </button>
                </div>
              </div>
            ) : (
              <div className="messages-list">
                {messages.map((message) => (
                  <div key={message.id} className={`message ${message.type}`}>
                    <div className="message-avatar">
                      <div className={`${message.type}-avatar`}>
                        {message.type === 'user' ? '👤' : '🤖'}
                      </div>
                    </div>
                    <div className="message-content">
                      <div className={`message-bubble ${message.type} ${message.isError ? 'error' : ''}`}>
                        <div className="message-text">
                          {message.content}
                        </div>
                        {message.file && (
                          <div className="file-attachment">
                            <div className="file-icon">📁</div>
                            <span className="file-name">{message.file.name}</span>
                            <span className="file-size">({(message.file.size / 1024).toFixed(1)}KB)</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                
                {loading && (
                  <div className="message ai">
                    <div className="message-avatar">
                      <div className="ai-avatar">🤖</div>
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
                  <span className="file-size">({(uploadedFile.size / 1024).toFixed(1)}KB)</span>
                </div>
                <button onClick={removeFile} className="remove-file">×</button>
              </div>
            )}
            
            <div className="input-container">
              <button 
                onClick={() => fileInputRef.current?.click()}
                className="attachment-btn"
                title="Upload File"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
                </svg>
              </button>
              
              <textarea
                ref={textareaRef}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your message here..."
                disabled={loading}
                className="message-input"
                rows="1"
              />
              
              <button 
                onClick={askAI}
                disabled={loading || (!question.trim() && !uploadedFile)}
                className="send-button"
                title="Send message"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M22 2L11 13"/>
                  <path d="M22 2L15 22L11 13L2 9L22 2z"/>
                </svg>
              </button>
            </div>
            
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
              accept="*/*"
            />
            
            <div className="input-footer">
              <span className="input-hint">
                Press Enter to send • Shift+Enter for new line • Max 10MB files
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;