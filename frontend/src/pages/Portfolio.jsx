import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getMyPortfolio } from '../api'
import { useAuth } from '../context/useAuth'

export default function Portfolio() {
  const { user } = useAuth()
  const [portfolio, setPortfolio] = useState(null)
  const [error, setError] = useState('')

  async function loadPortfolio() {
    try {
      const res = await getMyPortfolio()
      setPortfolio(res.data)
      setError('')
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load portfolio')
      setPortfolio(null)
    }
  }

  useEffect(() => {
    if (!user) return
    loadPortfolio()
  }, [user])

  if (!user) {
    return (
      <div>
        <h1 className="page-title">Portfolio</h1>
        <div className="card"><div className="empty">Please <Link to="/auth">login</Link> to view your portfolio.</div></div>
      </div>
    )
  }

  return (
    <div>
      <h1 className="page-title">Portfolio</h1>
      {error && <div className="alert alert-error">{error}</div>}

      {portfolio && (
        <>
          <div className="grid-2">
            <div className="card">
              <h2>Cash Balance</h2>
              <div className="balance-amount">${parseFloat(portfolio.cash_balance).toFixed(2)}</div>
            </div>
            <div className="card">
              <h2>Total Equity</h2>
              <div className="balance-amount">${parseFloat(portfolio.total_equity).toFixed(2)}</div>
            </div>
          </div>

          <div className="grid-2">
            <div className="card">
              <h2>Market Value</h2>
              <div className="balance-amount">${parseFloat(portfolio.total_market_value).toFixed(2)}</div>
            </div>
            <div className="card">
              <h2>Unrealized P/L</h2>
              <div className="balance-amount" style={{ color: parseFloat(portfolio.total_unrealized_pnl) >= 0 ? '#8cf2cb' : '#ffb3bf' }}>
                ${parseFloat(portfolio.total_unrealized_pnl).toFixed(2)}
              </div>
            </div>
          </div>

          <div className="card">
            <h2>Positions</h2>
            {portfolio.positions.length === 0 ? (
              <div className="empty">No positions yet. Buy assets to build a portfolio.</div>
            ) : (
              portfolio.positions.map((pos, idx) => (
                <div className="tx-item" key={idx}>
                  <div className="tx-info">
                    <span className="tx-type">{pos.asset_symbol}</span>
                    <span className="tx-meta">Qty: {pos.quantity} - Avg: ${parseFloat(pos.avg_buy_price).toFixed(2)}</span>
                    <span className="tx-meta">Market: ${parseFloat(pos.market_price).toFixed(2)} - Value: ${parseFloat(pos.market_value).toFixed(2)}</span>
                  </div>
                  <span className={`badge ${parseFloat(pos.unrealized_pnl) >= 0 ? 'badge-success' : 'badge-failure'}`}>
                    {parseFloat(pos.unrealized_pnl) >= 0 ? '+' : ''}${parseFloat(pos.unrealized_pnl).toFixed(2)}
                  </span>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  )
}
