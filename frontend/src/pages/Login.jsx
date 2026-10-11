import { Link, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { useAuthForm } from '../auth/useAuthForm.js'
import AuthCard from '../components/AuthCard.jsx'
import TextField from '../components/TextField.jsx'

export default function Login() {
  const { user, login } = useAuth()
  const location = useLocation()
  const form = useAuthForm({ email: '', password: '' }, login)

  // Once logged in (or if already logged in), go back to where the user was headed.
  if (user) {
    return <Navigate to={location.state?.from?.pathname ?? '/'} replace />
  }

  return (
    <AuthCard
      title="Log in"
      error={form.error}
      onSubmit={form.handleSubmit}
      submitLabel="Log in"
      submitting={form.submitting}
      footer={
        <>
          No account yet?{' '}
          <Link to="/signup" className="text-brand hover:underline">
            Sign up
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
        label="Password"
        id="password"
        type="password"
        autoComplete="current-password"
        required
        value={form.values.password}
        onChange={form.handleChange}
      />
    </AuthCard>
  )
}
