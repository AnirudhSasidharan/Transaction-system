import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import CreateTransaction from './pages/CreateTransaction'
import History from './pages/History'
import './App.css'

export default function App() {
  return (
    <div className="app">
      <nav className="navbar">
        <span className="brand">Transaction System</span>
        <div className="nav-links">
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/send">Send / Buy</NavLink>
          <NavLink to="/history">History</NavLink>
        </div>
      </nav>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/send" element={<CreateTransaction />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </main>
    </div>
  )
}
