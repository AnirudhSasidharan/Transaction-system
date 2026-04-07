import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api'
import { useAuth } from '../context/useAuth'

export default function AuthPage() {
  const { user, login, register, logout } = useAuth()
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ user_id: '', password: '', initial_balance: '1000' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleChange = (e) => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))

  const submit = async () => {
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') {
        await login(form.user_id, form.password)
      } else {
        await register(form.user_id, form.password, parseFloat(form.initial_balance))
      }
      navigate('/')
    } catch (e) {
      setError(getApiErrorMessage(e, 'Authentication failed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="page-title">Authentication</h1>

      {user ? (
        <div className="card">
          <h2>Signed in as {user.user_id}</h2>
          <div className="inline-actions">
            <button className="btn btn-primary" onClick={() => navigate('/')}>Go to Dashboard</button>
            <button className="btn" style={{ background: 'rgba(251,113,133,0.2)', color: '#ffd2db', border: '1px solid rgba(251,113,133,0.45)' }} onClick={logout}>Logout</button>
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="chip-group" style={{ marginBottom: '1rem' }}>
            <button className={`chip-btn ${mode === 'login' ? 'chip-btn-active' : ''}`} onClick={() => setMode('login')}>Login</button>
            <button className={`chip-btn ${mode === 'register' ? 'chip-btn-active' : ''}`} onClick={() => setMode('register')}>Register</button>
          </div>

          <div className="form-group">
            <label>User ID</label>
            <input name="user_id" value={form.user_id} onChange={handleChange} placeholder="e.g. trader_001" />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input type="password" name="password" value={form.password} onChange={handleChange} placeholder="at least 8 characters" />
          </div>

          {mode === 'register' && (
            <div className="form-group">
              <label>Initial Balance</label>
              <input type="number" name="initial_balance" value={form.initial_balance} onChange={handleChange} />
            </div>
          )}

          <button className="btn btn-primary" disabled={loading} onClick={submit}>
            {loading ? 'Please wait...' : mode === 'login' ? 'Login' : 'Create account'}
          </button>

          {error && <div className="alert alert-error" style={{ marginTop: '1rem' }}>{error}</div>}
        </div>
      )}
    </div>
  )
}
