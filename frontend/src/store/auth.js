import { reactive } from 'vue'

export const authStore = reactive({
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  token: localStorage.getItem('token') || null,

  setUser(user) {
    this.user = user
    if (user) localStorage.setItem('user', JSON.stringify(user))
    else localStorage.removeItem('user')
  },

  setToken(token) {
    this.token = token
    if (token) localStorage.setItem('token', token)
    else localStorage.removeItem('token')
  },

  logout() {
    this.setToken(null)
    this.setUser(null)
  },

  get isAdmin() {
    return this.user?.role === 'admin'
  },

  get isLoggedIn() {
    return !!this.token && !!this.user
  },
})
