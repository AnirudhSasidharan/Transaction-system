import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { connectWebSocket, getMyTransactionHistory, getMyWallet, topUpMyWallet } from '../api'
import { useAuth } from '../context/useAuth'

export default function Dashboard() {
  const { user } = useAuth()
  const [wallet, setWallet] = useState(null)
  const [error, setError] = useState('')
  const [topUpAmount, setTopUpAmount] = useState('')
  const [liveUpdates, setLiveUpdates] = useState([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)

  async function loadWallet() {
    try {
      const res = await getMyWallet()
      setWallet(res.data)
      setError('')
    } catch {
      setWallet(null)
      setError('Could not load wallet')
    }
  }

  async function loadRecentTransactions() {
    try {
      const res = await getMyTransactionHistory(10, 0)
      const recent = res.data.map((tx) => ({
        transaction_id: tx.id,
        status: tx.status,
        new_balance: null,
        failure_reason: tx.failure_reason,
      }))
      setLiveUpdates(recent)
    } catch {
      setLiveUpdates([])
    }
  }

  useEffect(() => {
    if (!user?.user_id) return
    loadWallet()
    loadRecentTransactions()
  }, [user?.user_id])

  useEffect(() => {
    if (!user?.user_id) return
    if (wsRef.current) wsRef.current.close()

    const ws = connectWebSocket(user.user_id, (data) => {
      if (!data?.transaction_id || !data?.status) return
      setLiveUpdates((prev) => [data, ...prev].slice(0, 10))

      if (data.status === 'success' && data.new_balance) {
        setWallet((prev) => (prev ? { ...prev, balance: data.new_balance } : prev))
      }
    })

    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    wsRef.current = ws

    return () => ws.close()
  }, [user?.user_id])

  async function handleTopUp() {
    if (!topUpAmount) return
    try {
      const res = await topUpMyWallet(parseFloat(topUpAmount))
      setWallet(res.data)
      setTopUpAmount('')
    } catch (e) {
      setError(e.response?.data?.detail || 'Top up failed')
    }
  }

  if (!user) {
    return (
      <div>
        <h1 className="page-title">Dashboard</h1>
        <div className="card">
          <div className="empty">
            Please <Link to="/auth">login</Link> to view your wallet and live transactions.
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>

      <div className="card">
        <h2>Active user</h2>
        <div className="chip-group">
          <div className="chip-btn chip-btn-active">{user.user_id}</div>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="grid-2">
        <div className="card">
          <h2>Balance</h2>
          {wallet ? (
            <div className="balance-amount">${parseFloat(wallet.balance).toFixed(2)}</div>
          ) : (
            <div className="empty">No wallet</div>
          )}
        </div>

        <div className="card">
          <h2>
            <span className="live-dot" style={{ background: connected ? '#4caf76' : '#f56565' }}></span>
            {connected ? 'Live updates connected' : 'Disconnected'}
          </h2>
          <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.3rem' }}>
            ws://localhost:8000/api/v1/ws/{user.user_id}
          </div>
        </div>
      </div>

      {wallet && (
        <div className="card">
          <h2>Top up wallet</h2>
          <div className="inline-actions">
            <input
              type="number"
              placeholder="Amount"
              value={topUpAmount}
              onChange={(e) => setTopUpAmount(e.target.value)}
              className="inline-input"
            />
            <button className="btn btn-primary" onClick={handleTopUp}>Add funds</button>
          </div>
        </div>
      )}

      <div className="card">
        <h2>
          <span className="live-dot"></span>
          Live transaction updates
        </h2>
        {liveUpdates.length === 0 ? (
          <div className="empty">No updates yet - create a transaction to see live updates here</div>
        ) : (
          liveUpdates.map((update, i) => {
            const txId = update.transaction_id ?? update.id ?? '?'
            const status = update.status ?? 'unknown'
            const newBal = update.new_balance
            const reason = update.failure_reason

            return (
              <div key={i} className="tx-item">
                <div className="tx-info">
                  <span className="tx-type">Transaction #{txId}</span>
                  <span className="tx-meta">
                    {reason
                      ? `Failed: ${reason}`
                      : newBal
                        ? `New balance: $${parseFloat(newBal).toFixed(2)}`
                        : status === 'processing'
                          ? 'Processing...'
                          : ''}
                  </span>
                </div>
                <span className={`badge badge-${status}`}>{status}</span>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
