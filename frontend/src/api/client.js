const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')
const ACCESS_TOKEN_KEY = 'artisan_connect.access_token'
const REFRESH_TOKEN_KEY = 'artisan_connect.refresh_token'
const USER_KEY = 'artisan_connect.user'

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

export const tokenStorage = {
  getAccessToken() {
    return sessionStorage.getItem(ACCESS_TOKEN_KEY)
  },
  getRefreshToken() {
    return sessionStorage.getItem(REFRESH_TOKEN_KEY)
  },
  getUser() {
    try {
      return JSON.parse(sessionStorage.getItem(USER_KEY))
    } catch {
      return null
    }
  },
  save({ access, refresh, user }) {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, access)
    sessionStorage.setItem(REFRESH_TOKEN_KEY, refresh)
    if (user) sessionStorage.setItem(USER_KEY, JSON.stringify(user))
  },
  updateAccessToken({ access, refresh }) {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, access)
    if (refresh) sessionStorage.setItem(REFRESH_TOKEN_KEY, refresh)
  },
  clear() {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY)
    sessionStorage.removeItem(REFRESH_TOKEN_KEY)
    sessionStorage.removeItem(USER_KEY)
  },
}

function apiUrl(path) {
  const endpoint = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${endpoint}`
}

function encodeBody(body) {
  if (body === undefined || body === null || typeof body === 'string' || body instanceof FormData) {
    return body
  }
  return JSON.stringify(body)
}

async function decodeResponse(response) {
  const contentType = response.headers.get('content-type') || ''
  return contentType.includes('application/json')
    ? response.json()
    : response.text()
}

function apiErrorMessage(data) {
  if (typeof data === 'string') return data
  if (data.detail || data.error) return data.detail || data.error
  const firstFieldError = Object.values(data).flat(Infinity).find((value) => typeof value === 'string')
  return firstFieldError || 'The request could not be completed.'
}

async function refreshAccessToken() {
  const refresh = tokenStorage.getRefreshToken()
  if (!refresh) return false

  const response = await fetch(apiUrl('/accounts/auth/refresh'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
  if (!response.ok) {
    tokenStorage.clear()
    window.dispatchEvent(new Event('artisan-auth-expired'))
    return false
  }

  tokenStorage.updateAccessToken(await response.json())
  return true
}

export async function apiRequest(path, options = {}, hasRetried = false) {
  const headers = new Headers(options.headers)
  const token = tokenStorage.getAccessToken()
  const hasBody = options.body !== undefined && options.body !== null
  const isFormData = hasBody && options.body instanceof FormData

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  if (hasBody && !isFormData && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(apiUrl(path), {
    ...options,
    headers,
    body: encodeBody(options.body),
  })

  if (
    response.status === 401
    && !hasRetried
    && tokenStorage.getRefreshToken()
    && !path.includes('/auth/login')
    && !path.includes('/auth/refresh')
  ) {
    const refreshed = await refreshAccessToken()
    if (refreshed) return apiRequest(path, options, true)
  }

  const data = await decodeResponse(response)

  if (!response.ok) {
    throw new ApiError(apiErrorMessage(data), response.status, data)
  }

  return data
}