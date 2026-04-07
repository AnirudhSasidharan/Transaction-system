import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getMyTransactionHistory } from '../api'
import { useAuth } from '../context/useAuth'

export default function History() {
  const { user } = useAuth()
  const [transactions, setTransactions] = useState([])
  const [error, setError] = useState('')
  const [offset, setOffset] = useState(0)
  const LIMIT = 10

  async function loadHistory() {
    try {
      const res = await getMyTransactionHistory(LIMIT, offset)
      setTransactions(res.data)
      setError('')
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load history')
      setTransactions([])
    }
  }

  useEffect(() => {
    if (!user) return
    loadHistory()
  }, [user, offset])

  const formatDate = (dateStr) => new Date(dateStr).toLocaleString()

  if (!user) {
    return (
      <div>
        <h1 className="page-title">Transaction history</h1>
        <div className="card"><div className="empty">Please <Link to="/auth">login</Link> to view history.</div></div>
      </div>
    )
  }

  return (
    <div>
      <h1 className="page-title">Transaction history</h1>

      <div className="card">
        <h2>Viewing history for</h2>
        <div className="chip-group">
          <div className="chip-btn chip-btn-active">{user.user_id}</div>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card">
        {transactions.length === 0 ? (
          <div className="empty">No transactions found</div>
        ) : (
          transactions.map((tx) => (
            <div key={tx.id} className="tx-item">
              <div className="tx-info">
                <span className="tx-type">
                  #{tx.id} - {tx.transaction_type}
                  {tx.asset_symbol ? ` - ${tx.asset_symbol}` : ''}
                  {tx.recipient_user_id ? ` -> ${tx.recipient_user_id}` : ''}
                </span>
                <span className="tx-meta">{formatDate(tx.created_at)}</span>
                {tx.failure_reason && (
                  <span className="tx-meta tx-error">{tx.failure_reason}</span>
                )}
              </div>
              <div className="tx-side">
                <span className={`badge badge-${tx.status}`}>{tx.status}</span>
                <span className="tx-amount">${parseFloat(tx.amount).toFixed(2)}</span>
              </div>
            </div>
          ))
        )}

        <div className="pager-row">
          <button
            className="btn"
            style={{ background: 'rgba(8, 24, 34, 0.95)', color: '#d4eaf5', border: '1px solid rgba(148, 163, 184, 0.25)' }}
            onClick={() => setOffset(Math.max(0, offset - LIMIT))}
            disabled={offset === 0}
          >
            Previous
          </button>
          <span className="pager-text">
            Showing {offset + 1}-{offset + transactions.length}
          </span>
          <button
            className="btn"
            style={{ background: 'rgba(8, 24, 34, 0.95)', color: '#d4eaf5', border: '1px solid rgba(148, 163, 184, 0.25)' }}
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
