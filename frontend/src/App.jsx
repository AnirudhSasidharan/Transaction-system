import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import CreateTransaction from './pages/CreateTransaction'
import History from './pages/History'
import Portfolio from './pages/Portfolio'
import AuthPage from './pages/Auth'
import { useAuth } from './context/useAuth'
import './App.css'

export default function App() {
  const { user } = useAuth()

  return (
    <div className="app">
      <div className="bg-orb orb-a" />
      <div className="bg-orb orb-b" />
      <div className="bg-grid" />

      <nav className="navbar">
        <span className="brand">Transaction System</span>
        <div className="nav-links">
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/send">Trade</NavLink>
          <NavLink to="/portfolio">Portfolio</NavLink>
          <NavLink to="/history">History</NavLink>
          <NavLink to="/auth">{user ? user.user_id : 'Login'}</NavLink>
        </div>
      </nav>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/send" element={<CreateTransaction />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/history" element={<History />} />
          <Route path="/auth" element={<AuthPage />} />
        </Routes>
      </main>
    </div>
  )
}
