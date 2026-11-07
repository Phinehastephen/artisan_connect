import { useEffect, useState } from 'react'
import { apiRequest } from '../api/client'

const emptyForm = {
  username: '',
  full_name: '',
  profile_picture: '',
  default_location: '',
}

export default function CustomerProfile() {
  const [profile, setProfile] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    let active = true

    apiRequest('/customers/customer/details')
      .then((customer) => {
        if (!active) return
        setProfile(customer)
        setForm({
          username: customer.user.username || '',
          full_name: customer.user.full_name || '',
          profile_picture: customer.user.profile_picture || '',
          default_location: customer.default_location || '',
        })
      })
      .catch((requestError) => {
        if (active) setError(requestError.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => { active = false }
  }, [])

  function updateField(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  async function saveProfile(event) {
    event.preventDefault()
    setError('')
    setNotice('')
    setSaving(true)
    try {
      const updatedProfile = await apiRequest('/customers/customer/details', {
        method: 'PATCH',
        body: form,
      })
      setProfile(updatedProfile)
      setNotice('Your profile has been updated.')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <p aria-live="polite" className="booking-loading" role="status">Loading your profile…</p>
  }

  return (
    <section aria-labelledby="customer-profile-title" className="customer-profile">
      <p className="eyebrow">YOUR ACCOUNT</p>
      <h1 id="customer-profile-title">Edit your profile</h1>
      <p className="page-intro">Keep your account details and customer profile up to date.</p>
      {notice && <div className="alert alert-success" role="status">{notice}</div>}
      {error && <div className="alert alert-danger" role="alert">{error}</div>}
      {profile && (
        <form className="customer-profile-form" onSubmit={saveProfile}>
          <div className="customer-profile-grid">
            <label className="form-label" htmlFor="customer-username">
              Username
              <input
                autoComplete="username"
                className="form-control"
                id="customer-username"
                maxLength={150}
                name="username"
                onChange={updateField}
                required
                value={form.username}
              />
            </label>
            <label className="form-label" htmlFor="customer-full-name">
              Full name
              <input
                autoComplete="name"
                className="form-control"
                id="customer-full-name"
                maxLength={150}
                name="full_name"
                onChange={updateField}
                required
                value={form.full_name}
              />
            </label>
            <label className="form-label" htmlFor="customer-profile-picture">
              Profile picture URL
              <input
                className="form-control"
                id="customer-profile-picture"
                maxLength={255}
                name="profile_picture"
                onChange={updateField}
                placeholder="https://…"
                value={form.profile_picture}
              />
            </label>
            <label className="form-label" htmlFor="customer-default-location">
              Default location
              <input
                className="form-control"
                id="customer-default-location"
                maxLength={255}
                name="default_location"
                onChange={updateField}
                value={form.default_location}
              />
            </label>
          </div>
          <div className="customer-profile-readonly">
            <div><span>Email</span><strong>{profile.user.email}</strong></div>
            <div><span>Phone number</span><strong>{profile.phone_number}</strong></div>
            <p className="field-note">
              Email and phone number are locked and cannot be changed here.
            </p>
          </div>
          <button className="btn btn-dark" disabled={saving} type="submit">
            {saving ? 'Saving…' : 'Save profile'}
          </button>
        </form>
      )}
    </section>
  )
}
