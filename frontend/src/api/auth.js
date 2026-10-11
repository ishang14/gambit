import { apiFetch } from './client.js'

export function signupRequest({ email, password, chesscomUsername }) {
  return apiFetch('/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ email, password, chesscom_username: chesscomUsername || null }),
  })
}

export function loginRequest({ email, password }) {
  return apiFetch('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function fetchMe() {
  return apiFetch('/auth/me')
}
