// src/api.js
// All calls to the backend API in one place.
// Every component imports from here — never fetch() directly in a component.

import axios from 'axios'

const BASE_URL = 'http://localhost:8000/api/v1'
const WS_URL = 'ws://localhost:8000/api/v1'

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// ── Wallets ───────────────────────────────────────────────────────────────────
export const createWallet = (userId, initialBalance = 1000) =>
  api.post('/wallets/', { user_id: userId, initial_balance: initialBalance })

export const getWallet = (userId) =>
  api.get(`/wallets/${userId}`)

export const topUpWallet = (userId, amount) =>
  api.post(`/wallets/${userId}/topup`, { amount })

// ── Transactions ──────────────────────────────────────────────────────────────
export const createTransaction = (data) =>
  api.post('/transactions/', data)

export const getTransaction = (transactionId) =>
  api.get(`/transactions/${transactionId}`)

export const getTransactionHistory = (userId, limit = 20, offset = 0) =>
  api.get(`/transactions/history/${userId}?limit=${limit}&offset=${offset}`)

// ── WebSocket ─────────────────────────────────────────────────────────────────
// Returns a WebSocket connection for a user
// Usage: const ws = connectWebSocket('user_001', (data) => console.log(data))
export const connectWebSocket = (userId, onMessage) => {
  const ws = new WebSocket(`${WS_URL}/ws/${userId}`)

  ws.onopen = () => console.log(`WebSocket connected for ${userId}`)

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'ping') return // ignore keepalive pings
    onMessage(data)
  }

  ws.onerror = (err) => console.error('WebSocket error:', err)
  ws.onclose = () => console.log('WebSocket disconnected')

  return ws
}
