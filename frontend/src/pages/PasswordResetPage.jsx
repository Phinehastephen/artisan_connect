import { useState } from 'react'
import { Link } from 'react-router-dom'
import { apiRequest } from '../api/client'

export default function PasswordResetPage() {
  const [step, setStep] = useState(1)
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setNotice('')
    setSubmitting(true)
    try {
      if (step === 1) {
        await apiRequest('/accounts/password-reset/request', {
          method: 'POST',
          body: { email },
        })
        setNotice('If an account exists for this email, a reset code has been sent.')
        setStep(2)
      } else if (step === 2) {
        const response = await apiRequest('/accounts/password-reset/verify', {
          method: 'POST',
          body: { email, code },
        })
        setResetToken(response.reset_token)
        setStep(3)
      } else {
        await apiRequest('/accounts/password-reset/confirm', {
          method: 'POST',
          body: {
            reset_token: resetToken,
            new_password: password,
            confirm_password: confirmPassword,
          },
        })
        setNotice('Password reset complete. You can now sign in.')
        setStep(4)
      }
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="auth-page" aria-labelledby="reset-title">
      <p className="eyebrow">ACCOUNT ACCESS</p>
      <h1 id="reset-title">Reset password</h1>
      <p className="page-intro">{[
        'Request a reset code by email.',
        'Enter the 6-digit code we sent.',
        'Choose a new password.',
        'Your password has been updated.',
      ][step - 1]}</p>

      {notice && <div className="alert alert-success" role="status">{notice}</div>}
      {error && <div className="alert alert-danger" role="alert">{error}</div>}

      {step < 4 && (
        <form className="auth-form" onSubmit={handleSubmit}>
          {step === 1 && (
            <div className="mb-3">
              <label className="form-label" htmlFor="reset-email">Email</label>
              <input autoComplete="email" className="form-control" id="reset-email" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
            </div>
          )}
          {step === 2 && (
            <>
              <div className="mb-3">
                <label className="form-label" htmlFor="reset-code">6-digit code</label>
                <input autoComplete="one-time-code" className="form-control" id="reset-code" inputMode="numeric" maxLength="6" onChange={(event) => setCode(event.target.value)} pattern="[0-9]{6}" required value={code} />
              </div>
              <p className="field-note">Code sent to {email}</p>
            </>
          )}
          {step === 3 && (
            <>
              <div className="mb-3">
                <label className="form-label" htmlFor="new-password">New password</label>
                <input autoComplete="new-password" className="form-control" id="new-password" minLength="8" onChange={(event) => setPassword(event.target.value)} required type="password" value={password} />
              </div>
              <div className="mb-3">
                <label className="form-label" htmlFor="confirm-password">Confirm password</label>
                <input autoComplete="new-password" className="form-control" id="confirm-password" minLength="8" onChange={(event) => setConfirmPassword(event.target.value)} required type="password" value={confirmPassword} />
              </div>
            </>
          )}
          <button className="btn btn-dark auth-submit" disabled={submitting} type="submit">
            {submitting ? 'Please wait…' : ['Send reset code', 'Verify code', 'Set password'][step - 1]}
          </button>
        </form>
      )}

      <p className="auth-switch"><Link to="/login">Back to sign in</Link></p>
    </section>
  )
}