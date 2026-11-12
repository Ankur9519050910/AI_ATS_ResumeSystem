
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { supabase } from '../services/supabase'
import './Auth.css'

function ResetPassword() {
  const navigate = useNavigate()

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setMessage('')

    if (password.length < 8) {
      setError('Password must contain at least 8 characters.')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setLoading(true)

    try {
      const { error } = await supabase.auth.updateUser({
        password: password,
      })

      if (error) throw error

      setMessage('Your password has been updated successfully!')

      setTimeout(() => {
        navigate('/dashboard')
      }, 1500)
    } catch (err) {
      setError(
        err.message || 'Unable to reset password. Please try again.'
      )
    } finally {
      setLoading(false)
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
          <p className="auth-eyebrow">ACCOUNT RECOVERY</p>
          <h1>Reset your password</h1>
          <p>
            Create a new password to regain access to your account.
          </p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="new-password">New password</label>

          <input
            id="new-password"
            type="password"
            autoComplete="new-password"
            placeholder="Enter your new password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={8}
            required
          />

          <label htmlFor="confirm-password">
            Confirm new password
          </label>

          <input
            id="confirm-password"
            type="password"
            autoComplete="new-password"
            placeholder="Confirm your new password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            minLength={8}
            required
          />

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
            disabled={loading}
          >
            {loading ? 'Updating password...' : 'Update password'}
          </button>
        </form>

        <Link to="/login" className="auth-back">
          ← Back to sign in
        </Link>

      </section>
    </main>
  )
}

export default ResetPassword
