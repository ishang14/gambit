import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { useAuthForm } from '../auth/useAuthForm.js'
import AuthCard from '../components/AuthCard.jsx'
import TextField from '../components/TextField.jsx'

export default function Signup() {
  const { user, signup } = useAuth()
  const form = useAuthForm({ email: '', password: '', chesscomUsername: '' }, signup)

  if (user) {
    return <Navigate to="/" replace />
  }

  return (
    <AuthCard
      title="Sign up"
      error={form.error}
      onSubmit={form.handleSubmit}
      submitLabel="Create account"
      submitting={form.submitting}
      footer={
        <>
          Already have an account?{' '}
          <Link to="/login" className="text-brand hover:underline">
            Log in
          </Link>
        </>
      }
    >
      <TextField
        label="Email"
        id="email"
        type="email"
        autoComplete="email"
        required
        value={form.values.email}
        onChange={form.handleChange}
      />
      <TextField
        label="Password (at least 8 characters)"
        id="password"
        type="password"
        autoComplete="new-password"
        required
        minLength={8}
        value={form.values.password}
        onChange={form.handleChange}
      />
      <TextField
        label="chess.com username (optional)"
        id="chesscomUsername"
        autoComplete="off"
        value={form.values.chesscomUsername}
        onChange={form.handleChange}
      />
    </AuthCard>
  )
}
