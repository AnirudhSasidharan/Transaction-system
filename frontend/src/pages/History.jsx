import { useState, useEffect } from 'react'
import { getTransactionHistory } from '../api'

export default function History() {
  const [userId, setUserId] = useState('user_001')
  const [transactions, setTransactions] = useState([])
  const [error, setError] = useState('')
  const [offset, setOffset] = useState(0)
  const LIMIT = 10

  useEffect(() => {
    loadHistory()
  }, [userId, offset])

  const loadHistory = async () => {
    try {
      const res = await getTransactionHistory(userId, LIMIT, offset)
      setTransactions(res.data)
      setError('')
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load history')
      setTransactions([])
    }
  }

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString()
  }

  return (
    <div>
      <h1 className="page-title">Transaction history</h1>

      {/* User selector */}
      <div className="card">
        <h2>View history for</h2>
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
          {['user_001', 'user_002', 'user_003'].map(u => (
            <button
              key={u}
              onClick={() => { setUserId(u); setOffset(0) }}
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

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card">
        {transactions.length === 0 ? (
          <div className="empty">No transactions found</div>
        ) : (
          transactions.map(tx => (
            <div key={tx.id} className="tx-item">
              <div className="tx-info">
                <span className="tx-type">
                  #{tx.id} — {tx.transaction_type}
                  {tx.asset_symbol ? ` · ${tx.asset_symbol}` : ''}
                  {tx.recipient_user_id ? ` → ${tx.recipient_user_id}` : ''}
                </span>
                <span className="tx-meta">{formatDate(tx.created_at)}</span>
                {tx.failure_reason && (
                  <span className="tx-meta" style={{ color: '#f56565' }}>{tx.failure_reason}</span>
                )}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.3rem' }}>
                <span className={`badge badge-${tx.status}`}>{tx.status}</span>
                <span className="tx-amount">${parseFloat(tx.amount).toFixed(2)}</span>
              </div>
            </div>
          ))
        )}

        {/* Pagination */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1rem' }}>
          <button
            className="btn"
            style={{ background: '#2d3148', color: 'white' }}
            onClick={() => setOffset(Math.max(0, offset - LIMIT))}
            disabled={offset === 0}
          >
            Previous
          </button>
          <span style={{ color: '#64748b', fontSize: '0.85rem', alignSelf: 'center' }}>
            Showing {offset + 1}–{offset + transactions.length}
          </span>
          <button
            className="btn"
            style={{ background: '#2d3148', color: 'white' }}
            onClick={() => setOffset(offset + LIMIT)}
            disabled={transactions.length < LIMIT}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
