import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiRequest } from '../api/client'

const emptyForm = {
  username: '',
  email: '',
  full_name: '',
  phone_number: '',
  password: '',
}

export default function RegisterPage() {
  const navigate = useNavigate()
  const [role, setRole] = useState('CUSTOMER')
  const [form, setForm] = useState(emptyForm)
  const [services, setServices] = useState([])
  const [selectedServices, setSelectedServices] = useState([])
  const [serviceError, setServiceError] = useState('')
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [loadingServices, setLoadingServices] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (role !== 'ARTISAN') return undefined
    let active = true
    setLoadingServices(true)
    apiRequest('/services/service')
      .then((items) => {
        if (active) setServices(items)
      })
      .catch((requestError) => {
        if (active) setServiceError(requestError.message)
      })
      .finally(() => {
        if (active) setLoadingServices(false)
      })
    return () => { active = false }
  }, [role])

  function toggleService(serviceId) {
    setSelectedServices((current) => current.includes(serviceId)
      ? current.filter((id) => id !== serviceId)
      : current.length < 3 ? [...current, serviceId] : current)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    const isArtisan = role === 'ARTISAN'
    try {
      const user = await apiRequest(`/accounts/register/${isArtisan ? 'artisan' : 'customer'}`, {
        method: 'POST',
        body: {
          ...form,
          ...(isArtisan ? { services: selectedServices } : {}),
        },
      })
      setSuccessMessage(isArtisan
        ? 'Your artisan account was created and is awaiting admin review.'
        : 'Your account was created. You can now sign in.')
      setForm(emptyForm)
      setSelectedServices([])
      if (user.role === 'CUSTOMER') navigate('/login', { state: { registered: true } })
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="auth-page auth-page-wide" aria-labelledby="register-title">
      <p className="eyebrow">JOIN THE MARKETPLACE</p>
      <h1 id="register-title">Create your account</h1>
      <p className="page-intro">Choose how you’ll use Artisan Connect.</p>

      <div aria-label="Account type" className="role-switch" role="group">
        <button
          aria-pressed={role === 'CUSTOMER'}
          className={`role-option${role === 'CUSTOMER' ? ' selected' : ''}`}
          onClick={() => setRole('CUSTOMER')}
          type="button"
        >
          <i aria-hidden="true" className="bi bi-person me-2" />Customer
        </button>
        <button
          aria-pressed={role === 'ARTISAN'}
          className={`role-option${role === 'ARTISAN' ? ' selected' : ''}`}
          onClick={() => setRole('ARTISAN')}
          type="button"
        >
          <i aria-hidden="true" className="bi bi-tools me-2" />Artisan
        </button>
      </div>

      {successMessage && <div className="alert alert-success" role="status">{successMessage}</div>}
      {error && <div className="alert alert-danger" role="alert">{error}</div>}

      <form className="auth-form register-form" onSubmit={handleSubmit}>
        <div className="row g-3">
          <div className="col-12 col-sm-6">
            <label className="form-label" htmlFor="register-name">Full name</label>
            <input className="form-control" id="register-name" onChange={(event) => setForm({ ...form, full_name: event.target.value })} required value={form.full_name} />
          </div>
          <div className="col-12 col-sm-6">
            <label className="form-label" htmlFor="register-username">Username</label>
            <input autoComplete="username" className="form-control" id="register-username" onChange={(event) => setForm({ ...form, username: event.target.value })} required value={form.username} />
          </div>
          <div className="col-12 col-sm-6">
            <label className="form-label" htmlFor="register-email">Email</label>
            <input autoComplete="email" className="form-control" id="register-email" onChange={(event) => setForm({ ...form, email: event.target.value })} required type="email" value={form.email} />
          </div>
          <div className="col-12 col-sm-6">
            <label className="form-label" htmlFor="register-phone">Phone number</label>
            <input autoComplete="tel" className="form-control" id="register-phone" onChange={(event) => setForm({ ...form, phone_number: event.target.value })} required type="tel" value={form.phone_number} />
          </div>
          <div className="col-12">
            <label className="form-label" htmlFor="register-password">Password</label>
            <input autoComplete="new-password" className="form-control" id="register-password" minLength="8" onChange={(event) => setForm({ ...form, password: event.target.value })} required type="password" value={form.password} />
          </div>
        </div>

        {role === 'ARTISAN' && (
          <fieldset className="service-picker">
            <legend>Services offered <span>(choose 1–3)</span></legend>
            {loadingServices && <p className="field-note">Loading active services…</p>}
            {serviceError && <p className="field-error" role="alert">{serviceError}</p>}
            <div className="service-options">
              {services.map((service) => (
                <label className="service-option" key={service.id}>
                  <input
                    checked={selectedServices.includes(service.id)}
                    disabled={!selectedServices.includes(service.id) && selectedServices.length === 3}
                    onChange={() => toggleService(service.id)}
                    type="checkbox"
                  />
                  <span>{service.name}</span>
                </label>
              ))}
            </div>
          </fieldset>
        )}

        <button
          className="btn btn-dark auth-submit"
          disabled={submitting || loadingServices || (role === 'ARTISAN' && selectedServices.length === 0)}
          type="submit"
        >
          {submitting ? 'Creating account…' : `Create ${role === 'ARTISAN' ? 'artisan' : 'customer'} account`}
        </button>
      </form>

      <p className="auth-switch">Already registered? <Link to="/login">Sign in</Link></p>
    </section>
  )
}