import axios from 'axios'

const BASE_URL = 'http://localhost:8000/api/v1'
const WS_URL = 'ws://localhost:8000/api/v1'

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

export const getApiErrorMessage = (error, fallback = 'Request failed') => {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg || JSON.stringify(item)).join('; ')
  }
  if (detail && typeof detail === 'object') {
    return detail.message || JSON.stringify(detail)
  }
  return fallback
}

export const getToken = () => localStorage.getItem('access_token')
export const setToken = (token) => localStorage.setItem('access_token', token)
export const clearToken = () => localStorage.removeItem('access_token')

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auth
export const registerUser = (payload) => api.post('/auth/register', payload)
export const loginUser = (payload) => api.post('/auth/login', payload)
export const getMe = () => api.get('/auth/me')

// Wallets
export const createWallet = (userId, initialBalance = 1000) =>
  api.post('/wallets/', { user_id: userId, initial_balance: initialBalance })

export const getWallet = (userId) => api.get(`/wallets/${userId}`)
export const getMyWallet = () => api.get('/wallets/me')

export const topUpWallet = (userId, amount) => api.post(`/wallets/${userId}/topup`, { amount })
export const topUpMyWallet = (amount) => api.post('/wallets/me/topup', { amount })

// Transactions
export const createTransaction = (data, idempotencyKey) =>
  api.post('/transactions/', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
  })

export const getTransaction = (transactionId) => api.get(`/transactions/${transactionId}`)

export const getTransactionHistory = (userId, limit = 20, offset = 0) =>
  api.get(`/transactions/history/${userId}?limit=${limit}&offset=${offset}`)

export const getMyTransactionHistory = (limit = 20, offset = 0) =>
  api.get(`/transactions/history/me?limit=${limit}&offset=${offset}`)

// Portfolio
export const getMyPortfolio = () => api.get('/portfolio/me')

// WebSocket
export const connectWebSocket = (userId, onMessage) => {
  const ws = new WebSocket(`${WS_URL}/ws/${userId}`)

  ws.onopen = () => console.log(`WebSocket connected for ${userId}`)

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'ping' || data.type === 'connected') return
    onMessage(data)
  }

  ws.onerror = (err) => console.error('WebSocket error:', err)
  ws.onclose = () => console.log('WebSocket disconnected')

  return ws
}
