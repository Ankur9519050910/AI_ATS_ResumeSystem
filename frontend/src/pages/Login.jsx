
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/useAuth'
import { supabase } from '../services/supabase'
import './Auth.css'

function Login() {
  const navigate = useNavigate()
  const { signIn } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const [resetLoading, setResetLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setMessage('')
    setLoading(true)

    try {
      await signIn(email.trim(), password)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || 'Unable to sign in. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  async function handleForgotPassword() {
    setError('')
    setMessage('')

    if (!email.trim()) {
      setError('Please enter your registered email address first.')
      return
    }

    setResetLoading(true)

    try {
      const { error } = await supabase.auth.resetPasswordForEmail(
        email.trim(),
        {
          redirectTo: `${window.location.origin}/reset-password`,
        }
      )

      if (error) throw error

      setMessage(
        'Password reset instructions have been sent. Please check your email.'
      )
    } catch (err) {
      setError(err.message || 'Unable to send password reset email.')
    } finally {
      setResetLoading(false)
    }
  }

  async function handleGoogleLogin() {
    setError('')
    setMessage('')
    setGoogleLoading(true)

    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/dashboard`,
        },
      })

      if (error) throw error
    } catch (err) {
      setError(err.message || 'Unable to sign in with Google.')
      setGoogleLoading(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <Link to="/" className="auth-brand">
          <span className="brand-icon">R</span>
          <span>ResumeAI</span>
        </Link>

        <div className="auth-heading">
          <p className="auth-eyebrow">WELCOME BACK</p>
          <h1>Sign in to your account</h1>
          <p>Continue working toward your next career opportunity.</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="email">Email address</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            placeholder="Enter your password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          <div className="auth-forgot-wrapper">
            <button
              type="button"
              className="auth-forgot"
              onClick={handleForgotPassword}
              disabled={resetLoading || loading || googleLoading}
            >
              {resetLoading ? 'Sending reset link...' : 'Forgot password?'}
            </button>
          </div>

          {error && (
            <p className="auth-error" role="alert">
              {error}
            </p>
          )}

          {message && (
            <p className="auth-success" role="status">
              {message}
            </p>
          )}

          <button
            className="auth-submit"
            type="submit"
            disabled={loading || googleLoading || resetLoading}
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div className="auth-divider">
          <span>OR</span>
        </div>

        <button
          className="google-submit"
          type="button"
          onClick={handleGoogleLogin}
          disabled={googleLoading || loading || resetLoading}
        >
          {googleLoading
            ? 'Connecting to Google...'
            : 'Continue with Google'}
        </button>

        <p className="auth-switch">
          Don't have an account? <Link to="/register">Create one</Link>
        </p>

        <Link to="/" className="auth-back">
          ← Back to home
        </Link>
      </section>
    </main>
  )
}

export default Login
