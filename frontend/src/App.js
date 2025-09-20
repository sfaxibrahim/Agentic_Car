import Home from './pages/Home.js';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LoginPage from './pages/auth/Login.js';
import RegisterPage from './pages/auth/Register.js';
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route path="/Home" element={<Home />} />
        <Route path="/register" element={<RegisterPage />} />
      </Routes>
    </Router>
 
  );

}

export default App;