import axios from 'axios'

// Базовый HTTP-клиент. Baseurl берётся из переменной окружения Vite —
// см. корневой .env.example (VITE_API_URL). Interceptor для JWT (access
// token в заголовке Authorization) добавится на Этапе 5 вместе с auth-фичей.
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})
