import { create } from 'zustand'

function loadFromStorage() {
  try {
    return {
      accessToken: localStorage.getItem('access_token') || null,
      refreshToken: localStorage.getItem('refresh_token') || null,
      user: JSON.parse(localStorage.getItem('user') || 'null'),
    }
  } catch {
    return { accessToken: null, refreshToken: null, user: null }
  }
}

const useAuthStore = create((set) => ({
  ...loadFromStorage(),
  isAuthenticated: !!localStorage.getItem('access_token'),

  login(tokens, user) {
    localStorage.setItem('access_token', tokens.access_token)
    localStorage.setItem('refresh_token', tokens.refresh_token)
    localStorage.setItem('user', JSON.stringify(user))
    set({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      user,
      isAuthenticated: true,
    })
  },

  logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    set({ accessToken: null, refreshToken: null, user: null, isAuthenticated: false })
  },
}))

export default useAuthStore
