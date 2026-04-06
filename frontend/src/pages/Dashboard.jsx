import { useState, useEffect, useRef } from 'react'
import { getWallet, createWallet, topUpWallet, connectWebSocket } from '../api'

export default function Dashboard() {
  const [userId, setUserId] = useState('user_001')
  const [wallet, setWallet] = useState(null)
  const [error, setError] = useState('')
  const [topUpAmount, setTopUpAmount] = useState('')
  const [liveUpdates, setLiveUpdates] = useState([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)

  // Load wallet on mount or user change
  useEffect(() => {
    loadWallet()
  }, [userId])

  // Connect WebSocket when userId changes
  useEffect(() => {
    if (wsRef.current) wsRef.current.close()

    const ws = connectWebSocket(userId, (data) => {
      // Add update to live feed
      setLiveUpdates(prev => [data, ...prev].slice(0, 10))

      // If transaction succeeded, refresh balance
      if (data.status === 'success' && data.new_balance) {
        setWallet(prev => prev ? { ...prev, balance: data.new_balance } : prev)
      }
    })

    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    wsRef.current = ws

    return () => ws.close()
  }, [userId])

  const loadWallet = async () => {
    try {
      const res = await getWallet(userId)
      setWallet(res.data)
      setError('')
    } catch {
      setWallet(null)
      setError(`No wallet found for "${userId}"`)
    }
  }

  const handleCreateWallet = async () => {
    try {
      const res = await createWallet(userId, 1000)
      setWallet(res.data)
      setError('')
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to create wallet')
    }
  }

  const handleTopUp = async () => {
    if (!topUpAmount) return
    try {
      const res = await topUpWallet(userId, parseFloat(topUpAmount))
      setWallet(res.data)
      setTopUpAmount('')
    } catch (e) {
      setError(e.response?.data?.detail || 'Top up failed')
    }
  }

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>

      {/* User selector */}
      <div className="card">
        <h2>Active user</h2>
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
          {['user_001', 'user_002', 'user_003'].map(u => (
            <button
              key={u}
              onClick={() => setUserId(u)}
              className="btn"
              style={{
                background: userId === u ? '#7c85f5' : '#2d3148',
                color: 'white',
                padding: '0.4rem 0.9rem',
                fontSize: '0.85rem',
              }}
            >
              {u}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="alert alert-error">
          {error}
          <button
            onClick={handleCreateWallet}
            style={{ marginLeft: '1rem', textDecoration: 'underline', background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}
          >
            Create wallet
          </button>
        </div>
      )}

      <div className="grid-2">
        {/* Wallet balance */}
        <div className="card">
          <h2>Balance</h2>
          {wallet ? (
            <div className="balance-amount">${parseFloat(wallet.balance).toFixed(2)}</div>
          ) : (
            <div className="empty">No wallet</div>
          )}
        </div>

        {/* WebSocket status */}
        <div className="card">
          <h2>
            <span className="live-dot" style={{ background: connected ? '#4caf76' : '#f56565' }}></span>
            {connected ? 'Live updates connected' : 'Disconnected'}
          </h2>
          <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.3rem' }}>
            Listening on ws://localhost:8000/api/v1/ws/{userId}
          </div>
        </div>
      </div>

      {/* Top up */}
      {wallet && (
        <div className="card">
          <h2>Top up wallet</h2>
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
            <input
              type="number"
              placeholder="Amount"
              value={topUpAmount}
              onChange={e => setTopUpAmount(e.target.value)}
              style={{ flex: 1, padding: '0.6rem', background: '#0f1117', border: '1px solid #2d3148', borderRadius: '8px', color: '#e2e8f0' }}
            />
            <button className="btn btn-primary" onClick={handleTopUp}>Add funds</button>
          </div>
        </div>
      )}

      {/* Live feed */}
      <div className="card">
        <h2>
          <span className="live-dot"></span>
          Live transaction updates
        </h2>
        {liveUpdates.length === 0 ? (
          <div className="empty">No updates yet — create a transaction to see live updates here</div>
        ) : (
          liveUpdates.map((update, i) => (
            <div key={i} className="tx-item">
              <div className="tx-info">
                <span className="tx-type">Transaction #{update.transaction_id}</span>
                <span className="tx-meta">
                  {update.failure_reason || (update.new_balance ? `New balance: $${parseFloat(update.new_balance).toFixed(2)}` : '')}
                </span>
              </div>
              <span className={`badge badge-${update.status}`}>{update.status}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
