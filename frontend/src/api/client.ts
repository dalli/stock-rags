import axios from 'axios'

// Determine API base URL
// In development with Vite dev server, use relative path (proxy handles it)
// In production (built with serve), use full URL to backend
const getApiBaseUrl = (): string => {
  // Check if we're in browser environment
  if (typeof window !== 'undefined') {
    // Check for environment variables first (set at build time)
    const envUrl = (import.meta as any).env?.VITE_API_URL || (import.meta as any).env?.VITE_API_BASE_URL
    
    if (envUrl) {
      return envUrl.endsWith('/api/v1') ? envUrl : `${envUrl}/api/v1`
    }
    
    // Check if we're in Vite development mode
    // In production build, MODE will be 'production' and DEV will be false
    const isDev = (import.meta as any).env?.MODE === 'development' || (import.meta as any).env?.DEV === true
    
    if (isDev) {
      // Development mode: use relative path - Vite proxy will handle it
      return '/api/v1'
    }
    
    // Production mode: use full URL to backend
    // Backend is exposed on localhost:8000
    return 'http://localhost:8000/api/v1'
  }
  
  // Server-side or fallback
  return '/api/v1'
}

const API_BASE = getApiBaseUrl()

// Log API base for debugging
if (typeof window !== 'undefined') {
  console.log('[API Client] Using API base URL:', API_BASE)
}

const client = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default client
