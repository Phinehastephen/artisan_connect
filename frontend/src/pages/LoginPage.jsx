import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { homeForRole, useAuth } from '../auth/AuthContext'

export default function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate replace to={homeForRole(user.role)} />

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const profile = await login(form.username, form.password)
      navigate(location.state?.from?.pathname || homeForRole(profile.role), { replace: true })
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="auth-page" aria-labelledby="login-title">
      <p className="eyebrow">YOUR MARKETPLACE</p>
      <h1 id="login-title">Welcome back</h1>
      <p className="page-intro">Sign in to continue to your Artisan Connect workspace.</p>

      <form className="auth-form" onSubmit={handleSubmit}>
        {error && <div className="alert alert-danger" role="alert">{error}</div>}
        <div className="mb-3">
          <label className="form-label" htmlFor="login-username">Username</label>
          <input
            autoComplete="username"
            className="form-control"
            id="login-username"
            name="username"
            onChange={(event) => setForm({ ...form, username: event.target.value })}
            required
            value={form.username}
          />
        </div>
        <div className="mb-2">
          <label className="form-label" htmlFor="login-password">Password</label>
          <input
            autoComplete="current-password"
            className="form-control"
            id="login-password"
            name="password"
            onChange={(event) => setForm({ ...form, password: event.target.value })}
            required
            type="password"
            value={form.password}
          />
        </div>
        <div className="form-utility-row">
          <Link to="/password-reset">Forgot password?</Link>
        </div>
        <button className="btn btn-dark auth-submit" disabled={submitting} type="submit">
          {submitting ? 'Signing in…' : 'Sign in'}
          {!submitting && <i aria-hidden="true" className="bi bi-arrow-right ms-2" />}
        </button>
      </form>

      <p className="auth-switch">
        New to Artisan Connect? <Link to="/register">Create an account</Link>
      </p>
    </section>
  )
}