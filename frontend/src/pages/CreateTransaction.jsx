import { useState } from 'react'
import { createTransaction } from '../api'

export default function CreateTransaction() {
  const [form, setForm] = useState({
    user_id: 'user_001',
    transaction_type: 'buy',
    amount: '',
    asset_symbol: '',
    recipient_user_id: '',
  })
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async () => {
    setError('')
    setResult(null)
    setLoading(true)

    try {
      const payload = {
        user_id: form.user_id,
        transaction_type: form.transaction_type,
        amount: parseFloat(form.amount),
      }

      if (form.transaction_type === 'buy') {
        payload.asset_symbol = form.asset_symbol
      } else {
        payload.recipient_user_id = form.recipient_user_id
      }

      const res = await createTransaction(payload)
      setResult(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Transaction failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="page-title">Send / Buy</h1>

      <div className="card">
        <div className="form-group">
          <label>From user</label>
          <select name="user_id" value={form.user_id} onChange={handleChange}>
            <option>user_001</option>
            <option>user_002</option>
            <option>user_003</option>
          </select>
        </div>

        <div className="form-group">
          <label>Transaction type</label>
          <select name="transaction_type" value={form.transaction_type} onChange={handleChange}>
            <option value="buy">Buy asset</option>
            <option value="send">Send money</option>
          </select>
        </div>

        <div className="form-group">
          <label>Amount ($)</label>
          <input
            type="number"
            name="amount"
            placeholder="e.g. 200"
            value={form.amount}
            onChange={handleChange}
          />
        </div>

        {form.transaction_type === 'buy' && (
          <div className="form-group">
            <label>Asset symbol</label>
            <input
              type="text"
              name="asset_symbol"
              placeholder="e.g. BTC, ETH, AAPL"
              value={form.asset_symbol}
              onChange={handleChange}
            />
          </div>
        )}

        {form.transaction_type === 'send' && (
          <div className="form-group">
            <label>Recipient user ID</label>
            <select name="recipient_user_id" value={form.recipient_user_id} onChange={handleChange}>
              <option value="">Select recipient</option>
              <option value="user_001">user_001</option>
              <option value="user_002">user_002</option>
              <option value="user_003">user_003</option>
            </select>
          </div>
        )}

        <button
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading ? 'Submitting...' : 'Submit transaction'}
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {result && (
        <div className="card">
          <div className="alert alert-info" style={{ marginBottom: '1rem' }}>
            Transaction submitted — check Dashboard for live status updates
          </div>
          <div className="tx-item">
            <div className="tx-info">
              <span className="tx-type">#{result.id} — {result.transaction_type}</span>
              <span className="tx-meta">
                {result.asset_symbol || result.recipient_user_id} · ${parseFloat(result.amount).toFixed(2)}
              </span>
            </div>
            <span className={`badge badge-${result.status}`}>{result.status}</span>
          </div>
        </div>
      )}
    </div>
  )
}
