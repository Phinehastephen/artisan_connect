import { useEffect, useState } from 'react'
import { apiRequest } from '../api/client'
import './artisan-workspace.css'

const actionsByStatus = {
  PENDING: [
    { action: 'accept', label: 'Accept request', style: 'primary' },
    { action: 'reject', label: 'Decline', style: 'outline-danger' },
  ],
  ACCEPTED: [{ action: 'on-the-way', label: 'Mark on my way', style: 'primary' }],
  ON_THE_WAY: [{ action: 'start', label: 'Start job', style: 'primary' }],
  IN_PROGRESS: [{ action: 'complete', label: 'Mark complete', style: 'success' }],
}

function formatDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function customerName(booking) {
  return booking.customer_detail?.user?.full_name || 'Customer'
}

function ArtisanProfileEditor({ profile, onSaved }) {
  const [form, setForm] = useState({
    full_name: profile.user?.full_name || '',
    profile_picture: profile.user?.profile_picture || '',
    business_name: profile.business_name || '',
    phone_number: profile.phone_number || '',
    default_location: profile.default_location || '',
    latitude: profile.latitude ?? '',
    longitude: profile.longitude ?? '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  function updateField(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  async function saveProfile(event) {
    event.preventDefault()
    setError('')
    if ((form.latitude === '') !== (form.longitude === '')) {
      setError('Enter both coordinates, or clear both coordinates.')
      return
    }

    setSaving(true)
    try {
      const body = {
        ...form,
        latitude: form.latitude === '' ? null : Number(form.latitude),
        longitude: form.longitude === '' ? null : Number(form.longitude),
      }
      const updatedProfile = await apiRequest('/artisans/me', {
        method: 'PATCH',
        body,
      })
      onSaved(updatedProfile)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSaving(false)
    }
  }

  const canEdit = profile.verification_status === 'VERIFIED'

  return (
    <form className="artisan-profile-form" onSubmit={saveProfile}>
      <h3>Edit your profile</h3>
      {!canEdit && (
        <p className="field-note">
          Profile editing is available after your artisan account is verified.
        </p>
      )}
      {error && <div className="alert alert-danger" role="alert">{error}</div>}
      <div className="artisan-profile-form-grid">
        <label className="form-label" htmlFor="artisan-full-name">
          Full name
          <input
            autoComplete="name"
            className="form-control"
            disabled={!canEdit || saving}
            id="artisan-full-name"
            maxLength={150}
            name="full_name"
            onChange={updateField}
            required
            value={form.full_name}
          />
        </label>
        <label className="form-label" htmlFor="artisan-business-name">
          Business name
          <input
            className="form-control"
            disabled={!canEdit || saving}
            id="artisan-business-name"
            maxLength={150}
            name="business_name"
            onChange={updateField}
            value={form.business_name}
          />
        </label>
        <label className="form-label" htmlFor="artisan-phone-number">
          Phone number
          <input
            autoComplete="tel"
            className="form-control"
            disabled={!canEdit || saving}
            id="artisan-phone-number"
            maxLength={20}
            name="phone_number"
            onChange={updateField}
            required
            value={form.phone_number}
          />
        </label>
        <label className="form-label" htmlFor="artisan-profile-picture">
          Profile picture URL
          <input
            className="form-control"
            disabled={!canEdit || saving}
            id="artisan-profile-picture"
            maxLength={255}
            name="profile_picture"
            onChange={updateField}
            placeholder="https://…"
            value={form.profile_picture}
          />
        </label>
        <label className="form-label artisan-profile-location" htmlFor="artisan-default-location">
          Service area
          <input
            className="form-control"
            disabled={!canEdit || saving}
            id="artisan-default-location"
            maxLength={255}
            name="default_location"
            onChange={updateField}
            value={form.default_location}
          />
        </label>
        <label className="form-label" htmlFor="artisan-latitude">
          Latitude
          <input
            className="form-control"
            disabled={!canEdit || saving}
            id="artisan-latitude"
            max="90"
            min="-90"
            name="latitude"
            onChange={updateField}
            step="any"
            type="number"
            value={form.latitude}
          />
        </label>
        <label className="form-label" htmlFor="artisan-longitude">
          Longitude
          <input
            className="form-control"
            disabled={!canEdit || saving}
            id="artisan-longitude"
            max="180"
            min="-180"
            name="longitude"
            onChange={updateField}
            step="any"
            type="number"
            value={form.longitude}
          />
        </label>
      </div>
      <p className="field-note">
        Full name, profile picture, and business name each have a separate six-month change limit. Phone and service location do not.
      </p>
      <button className="btn btn-dark" disabled={!canEdit || saving} type="submit">
        {saving ? 'Saving…' : 'Save profile'}
      </button>
    </form>
  )
}

function ServiceChangeRequestForm({
  profile,
  availableServices,
  requests,
  onCreated,
}) {
  const currentIds = (profile.services || []).map((service) => String(service.id))
  const [selectedServices, setSelectedServices] = useState(currentIds)
  const [serviceSearch, setServiceSearch] = useState('')
  const [reason, setReason] = useState('')
  const [evidence, setEvidence] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const pendingRequest = requests.find((request) => request.status === 'PENDING')
  const latestApproval = requests
    .filter((request) => request.status === 'APPROVED' && request.reviewed_at)
    .sort((left, right) => new Date(right.reviewed_at) - new Date(left.reviewed_at))[0]
  const retainedCurrentCount = selectedServices.filter((id) => currentIds.includes(id)).length
  const newServiceCount = selectedServices.filter((id) => !currentIds.includes(id)).length
  const removedCurrentCount = currentIds.length - retainedCurrentCount
  const canRequestChange = profile.verification_status === 'VERIFIED'
    && !pendingRequest
  const filteredServices = availableServices
    .filter((service) => service.name.toLowerCase().includes(serviceSearch.trim().toLowerCase()))
    .sort((left, right) => left.name.localeCompare(right.name))
  const serviceGroups = filteredServices.reduce((groups, service) => {
    const firstLetter = service.name.trim().charAt(0).toUpperCase()
    const heading = /[A-Z]/.test(firstLetter) ? firstLetter : '#'
    groups[heading] = [...(groups[heading] || []), service]
    return groups
  }, {})

  function updateEvidence(category, files) {
    setEvidence((current) => ({ ...current, [category]: Array.from(files) }))
  }

  async function submitChangeRequest(event) {
    event.preventDefault()
    const formElement = event.currentTarget
    setError('')
    setNotice('')
    if (selectedServices.length < 1 || selectedServices.length > 3) {
      setError('Choose between one and three services for your proposed service list.')
      return
    }
    if (retainedCurrentCount < 1 || newServiceCount < 1 || removedCurrentCount < 1) {
      setError('A request must replace at least one current service and include at least one new service.')
      return
    }
    const categories = Object.entries(evidence).filter(([, files]) => files.length > 0)
    if (categories.length < 2) {
      setError('Upload evidence from at least two of the three qualification categories.')
      return
    }

    const body = new FormData()
    selectedServices.forEach((serviceId) => body.append('services', serviceId))
    body.append('reason', reason)
    categories.forEach(([category, files]) => {
      files.forEach((file) => body.append(category, file))
    })

    setSubmitting(true)
    try {
      const createdRequest = await apiRequest('/artisans/service-change-requests', {
        method: 'POST',
        body,
      })
      onCreated(createdRequest)
      formElement.reset()
      setReason('')
      setEvidence({})
      setNotice('Your service change request was submitted for admin review.')
      setSelectedServices(currentIds)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="artisan-service-change">
      <h3>Request a service change</h3>
      <p className="field-note">
        Submit your complete proposed list (up to three services). An admin reviews the request; services do not change until it is approved.
      </p>
      {latestApproval && (
        <p className="field-note">
          Most recent approval: {formatDate(latestApproval.reviewed_at)}. The API enforces the 12-month interval before another request can be submitted.
        </p>
      )}
      {!canRequestChange && (
        <p className="artisan-service-change-notice">
          {pendingRequest
            ? 'You already have a pending service change request.'
            : 'Service change requests are available after your artisan account is verified.'}
        </p>
      )}
      {notice && <div className="alert alert-success" role="status">{notice}</div>}
      {error && <div className="alert alert-danger" role="alert">{error}</div>}
      <form onSubmit={submitChangeRequest}>
        <div className="artisan-service-picker-heading">
          <label className="form-label" htmlFor="artisan-service-search">
            Find a service
            <input
              autoComplete="off"
              className="form-control"
              disabled={!canRequestChange || submitting}
              id="artisan-service-search"
              onChange={(event) => setServiceSearch(event.target.value)}
              placeholder="Search services by name"
              type="search"
              value={serviceSearch}
            />
          </label>
          <span className="artisan-service-selection-count">
            {selectedServices.length} of 3 selected
          </span>
        </div>
        <p className="field-note">
          Select up to three. Services are listed alphabetically; search to narrow the list.
        </p>
        {Object.keys(serviceGroups).length ? (
          <div className="artisan-service-groups">
            {Object.entries(serviceGroups).map(([heading, groupServices]) => (
              <fieldset className="artisan-service-group" key={heading}>
                <legend>{heading}</legend>
                <div className="artisan-service-options">
                  {groupServices.map((service) => {
                    const serviceId = String(service.id)
                    const selected = selectedServices.includes(serviceId)
                    return (
                      <label className={selected ? 'selected' : ''} key={service.id}>
                        <input
                          checked={selected}
                          disabled={
                            !canRequestChange
                            || submitting
                            || (!selected && selectedServices.length >= 3)
                          }
                          onChange={(event) => {
                            setSelectedServices((current) => (
                              event.target.checked
                                ? [...current, serviceId]
                                : current.filter((id) => id !== serviceId)
                            ))
                          }}
                          type="checkbox"
                        />
                        <span>{service.name}</span>
                      </label>
                    )
                  })}
                </div>
              </fieldset>
            ))}
          </div>
        ) : (
          <p className="artisan-service-empty">
            {serviceSearch ? 'No services match your search.' : 'No active services are available.'}
          </p>
        )}
        <p className="field-note">Your current services: {(profile.services || []).map((service) => service.name).join(', ') || 'None'}.</p>
        <label className="form-label" htmlFor="artisan-service-change-reason">
          Reason for the change
          <textarea
            className="form-control"
            disabled={!canRequestChange || submitting}
            id="artisan-service-change-reason"
            onChange={(event) => setReason(event.target.value)}
            required
            rows={3}
            value={reason}
          />
        </label>
        <div className="artisan-evidence-grid">
          <label className="form-label" htmlFor="artisan-trade-evidence">
            Trade qualification
            <input
              accept=".pdf,.jpg,.jpeg,.png,.webp"
              className="form-control"
              disabled={!canRequestChange || submitting}
              id="artisan-trade-evidence"
              multiple
              onChange={(event) => updateEvidence('trade_certificate', event.target.files)}
              type="file"
            />
          </label>
          <label className="form-label" htmlFor="artisan-training-evidence">
            Training or apprenticeship
            <input
              accept=".pdf,.jpg,.jpeg,.png,.webp"
              className="form-control"
              disabled={!canRequestChange || submitting}
              id="artisan-training-evidence"
              multiple
              onChange={(event) => updateEvidence('training_completion', event.target.files)}
              type="file"
            />
          </label>
          <label className="form-label" htmlFor="artisan-portfolio-evidence">
            Portfolio or work experience
            <input
              accept=".pdf,.jpg,.jpeg,.png,.webp"
              className="form-control"
              disabled={!canRequestChange || submitting}
              id="artisan-portfolio-evidence"
              multiple
              onChange={(event) => updateEvidence('portfolio_experience', event.target.files)}
              type="file"
            />
          </label>
        </div>
        <p className="field-note">
          Evidence is required from at least two categories. Accepted files: PDF, JPG, PNG, or WebP (up to 10 MB per file).
        </p>
        <button className="btn btn-outline-dark" disabled={!canRequestChange || submitting} type="submit">
          {submitting ? 'Submitting…' : 'Submit for review'}
        </button>
      </form>
      <div aria-label="Previous service change requests" className="artisan-service-request-list">
        <h4>Request history</h4>
        {requests.length ? requests.map((request) => (
          <article className="artisan-service-request-card" key={request.id}>
            <div>
              <strong>{request.status}</strong>
              <span>{formatDate(request.created_at)}</span>
            </div>
            <p>{request.services.map((service) => service.name).join(', ')}</p>
            {request.reason && <small>{request.reason}</small>}
          </article>
        )) : <p className="field-note">You have not submitted a service change request.</p>}
      </div>
    </div>
  )
}

export default function ArtisanWorkspacePage() {
  const [profile, setProfile] = useState(null)
  const [bookings, setBookings] = useState([])
  const [reviews, setReviews] = useState([])
  const [serviceChangeRequests, setServiceChangeRequests] = useState([])
  const [availableServices, setAvailableServices] = useState([])
  const [activeSection, setActiveSection] = useState('jobs')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [actionId, setActionId] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function loadWorkspace(isRefresh = false) {
    setError('')
    if (isRefresh) setRefreshing(true)
    else setLoading(true)
    try {
      const [artisanProfile, artisanBookings, allReviews, changeRequests, services] = await Promise.all([
        apiRequest('/artisans/me'),
        apiRequest('/bookings/list'),
        apiRequest('/reviews/review/create'),
        apiRequest('/artisans/service-change-requests'),
        apiRequest('/services/service'),
      ])
      setProfile(artisanProfile)
      setBookings(artisanBookings)
      setReviews(allReviews.filter((review) => review.artisan === artisanProfile.id))
      setServiceChangeRequests(changeRequests)
      setAvailableServices(services)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    let active = true
    Promise.all([
      apiRequest('/artisans/me'),
      apiRequest('/bookings/list'),
      apiRequest('/reviews/review/create'),
      apiRequest('/artisans/service-change-requests'),
      apiRequest('/services/service'),
    ])
      .then(([artisanProfile, artisanBookings, allReviews, changeRequests, services]) => {
        if (!active) return
        setProfile(artisanProfile)
        setBookings(artisanBookings)
        setReviews(allReviews.filter((review) => review.artisan === artisanProfile.id))
        setServiceChangeRequests(changeRequests)
        setAvailableServices(services)
      })
      .catch((requestError) => {
        if (active) setError(requestError.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [])

  async function handleBookingAction(booking, action) {
    setError('')
    setNotice('')
    setActionId(booking.id)
    try {
      const updatedBooking = await apiRequest(
        `/bookings/status/${booking.id}/${action}`,
        { method: 'POST' },
      )
      setBookings((current) => current.map((item) => (
        item.id === booking.id ? updatedBooking : item
      )))
      const actionLabel = action === 'reject'
        ? 'declined'
        : action === 'on-the-way'
          ? 'marked as on the way'
          : `${action}ed`
      setNotice(`Booking #${booking.id} ${actionLabel}.`)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setActionId(null)
    }
  }

  const pendingCount = bookings.filter((booking) => booking.status === 'PENDING').length
  const activeBookings = bookings.filter((booking) => (
    ['ACCEPTED', 'IN_PROGRESS', 'COMPLETED', 'DISPUTED'].includes(booking.status)
  ))
  const averageRating = reviews.length
    ? (reviews.reduce((total, review) => total + Number(review.rating), 0) / reviews.length).toFixed(1)
    : null

  return (
    <div className="artisan-workspace">
      <header className="artisan-welcome">
        <div>
          <p className="eyebrow">ARTISAN WORKSPACE</p>
          <h1>Welcome{profile?.user?.full_name ? `, ${profile.user.full_name}` : ' back'}.</h1>
          <p className="page-intro">Keep track of requests and the work you have underway.</p>
        </div>
        {profile && (
          <span className="artisan-verification-badge">
            <i aria-hidden="true" className="bi bi-patch-check-fill" />
            {profile.verification_status}
          </span>
        )}
      </header>

      <nav aria-label="Artisan workspace" className="artisan-workspace-nav">
        <button
          aria-current={activeSection === 'jobs' ? 'page' : undefined}
          className={activeSection === 'jobs' ? 'active' : ''}
          onClick={() => setActiveSection('jobs')}
          type="button"
        >
          <i aria-hidden="true" className="bi bi-briefcase me-2" />
          Jobs
          {pendingCount > 0 && <span className="artisan-nav-count">{pendingCount}</span>}
        </button>
        <button
          aria-current={activeSection === 'profile' ? 'page' : undefined}
          className={activeSection === 'profile' ? 'active' : ''}
          onClick={() => setActiveSection('profile')}
          type="button"
        >
          <i aria-hidden="true" className="bi bi-person me-2" />
          My profile
        </button>
        <button
          aria-current={activeSection === 'reviews' ? 'page' : undefined}
          className={activeSection === 'reviews' ? 'active' : ''}
          onClick={() => setActiveSection('reviews')}
          type="button"
        >
          <i aria-hidden="true" className="bi bi-star me-2" />
          Reviews
        </button>
      </nav>

      {notice && <div className="alert alert-success" role="status">{notice}</div>}
      {error && <div className="alert alert-danger" role="alert">{error}</div>}

      {loading ? (
        <p aria-live="polite" className="booking-loading" role="status">Loading your workspace…</p>
      ) : (
        <>
          {activeSection === 'jobs' && (
            <section aria-labelledby="artisan-jobs-title" className="artisan-section">
              <div className="results-heading">
                <div>
                  <p className="eyebrow">BOOKING MANAGEMENT</p>
                  <h2 id="artisan-jobs-title">Your jobs</h2>
                  <p className="page-intro">Accept or decline new requests, then update each job as it progresses.</p>
                </div>
                <button
                  className="btn btn-outline-dark"
                  disabled={refreshing}
                  onClick={() => loadWorkspace(true)}
                  type="button"
                >
                  <i aria-hidden="true" className="bi bi-arrow-clockwise me-1" />
                  {refreshing ? 'Refreshing…' : 'Refresh'}
                </button>
              </div>

              {bookings.length === 0 ? (
                <div className="empty-results">
                  <i aria-hidden="true" className="bi bi-inbox" />
                  <h3>No booking requests yet</h3>
                  <p>New customer requests will appear here.</p>
                </div>
              ) : (
                <div className="artisan-job-list">
                  {bookings.map((booking) => {
                    const workflowStatus = booking.workflow_status || booking.status
                    const actions = actionsByStatus[workflowStatus] || []
                    const isSubmitting = actionId === booking.id
                    return (
                      <article className="artisan-job-card" key={booking.id}>
                        <div className="artisan-job-header">
                          <div>
                            <p className="booking-reference">BOOKING #{booking.id}</p>
                            <h3>{booking.service_detail?.name || 'Service request'}</h3>
                            <p className="booking-artisan">Requested by {customerName(booking)}</p>
                          </div>
                          <span className={`booking-status status-${workflowStatus.toLowerCase()}`}>
                            {workflowStatus === 'ON_THE_WAY' ? 'On my way' : workflowStatus.replaceAll('_', ' ')}
                          </span>
                        </div>
                        <dl className="booking-details">
                          <div>
                            <dt>Requested</dt>
                            <dd>{formatDate(booking.created_at)}</dd>
                          </div>
                          {booking.job_address && (
                            <div>
                              <dt>Job location</dt>
                              <dd>{booking.job_address}</dd>
                            </div>
                          )}
                          {booking.completed_at && (
                            <div>
                              <dt>Marked complete</dt>
                              <dd>{formatDate(booking.completed_at)}</dd>
                            </div>
                          )}
                          {booking.artisan_on_the_way_at && (
                            <div>
                              <dt>Artisan on the way</dt>
                              <dd>{formatDate(booking.artisan_on_the_way_at)}</dd>
                            </div>
                          )}
                          {booking.scope_answers?.length > 0 && (
                            <div className="artisan-job-scope">
                              <dt>Requested job details</dt>
                              <dd>
                                {booking.scope_answers.map((answer) => (
                                  <span key={answer.key}>{answer.question}: {answer.answer}</span>
                                ))}
                              </dd>
                            </div>
                          )}
                        </dl>
                        {booking.status === 'COMPLETED' && (
                          <p className="artisan-job-note">
                            Waiting for the customer to confirm completion or raise a dispute.
                          </p>
                        )}
                        {booking.status === 'DISPUTED' && (
                          <div className="artisan-dispute-note">
                            <strong>Customer dispute</strong>
                            <p>{booking.dispute_reason}</p>
                          </div>
                        )}
                        {actions.length > 0 && (
                          <div className="artisan-job-actions">
                            {actions.map(({ action, label, style }) => (
                              <button
                                className={`btn btn-${style}`}
                                disabled={isSubmitting}
                                key={action}
                                onClick={() => handleBookingAction(booking, action)}
                                type="button"
                              >
                                {isSubmitting ? 'Updating…' : label}
                              </button>
                            ))}
                          </div>
                        )}
                      </article>
                    )
                  })}
                </div>
              )}
            </section>
          )}

          {activeSection === 'profile' && profile && (
            <section aria-labelledby="artisan-profile-title" className="artisan-section">
              <p className="eyebrow">YOUR BUSINESS</p>
              <h2 id="artisan-profile-title">Profile overview</h2>
              <div className="artisan-profile-card">
                <div className="artisan-profile-heading">
                  <div className="artisan-avatar" aria-hidden="true">
                    {(profile.business_name || profile.user?.full_name || 'A').trim().charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <h3>{profile.business_name || profile.user?.full_name}</h3>
                    <span className="verified-label">
                      <i aria-hidden="true" className="bi bi-patch-check-fill" />
                      {profile.verification_status}
                    </span>
                  </div>
                </div>
                <dl className="artisan-profile-details">
                  <div><dt>Service area</dt><dd>{profile.default_location || 'Not set'}</dd></div>
                  <div>
                    <dt>Service price references</dt>
                    <dd>
                      {profile.starting_price == null || profile.maximum_price == null
                        ? 'Not available'
                        : `₦${Number(profile.starting_price).toLocaleString()} – ₦${Number(profile.maximum_price).toLocaleString()}`}
                    </dd>
                  </div>
                  <div className="artisan-profile-services">
                    <dt>Services</dt>
                    <dd>
                      {profile.services?.length
                        ? profile.services.map((service) => service.name).join(', ')
                        : 'No services listed'}
                    </dd>
                  </div>
                </dl>
                <ArtisanProfileEditor
                  onSaved={(updatedProfile) => {
                    setProfile(updatedProfile)
                    setNotice('Your profile has been updated.')
                    setError('')
                  }}
                  profile={profile}
                />
                <ServiceChangeRequestForm
                  availableServices={availableServices}
                  onCreated={(createdRequest) => setServiceChangeRequests((current) => [createdRequest, ...current])}
                  profile={profile}
                  requests={serviceChangeRequests}
                />
              </div>
              <div className="artisan-profile-stats">
                <div><strong>{bookings.length}</strong><span>Total bookings</span></div>
                <div><strong>{activeBookings.length}</strong><span>Open jobs</span></div>
                <div><strong>{averageRating || '—'}</strong><span>Average rating</span></div>
              </div>
            </section>
          )}

          {activeSection === 'reviews' && (
            <section aria-labelledby="artisan-reviews-title" className="artisan-section">
              <p className="eyebrow">CUSTOMER FEEDBACK</p>
              <h2 id="artisan-reviews-title">Your reviews</h2>
              <p className="page-intro">Feedback customers have left on their bookings.</p>
              {reviews.length === 0 ? (
                <div className="empty-results">
                  <i aria-hidden="true" className="bi bi-star" />
                  <h3>No reviews yet</h3>
                  <p>Customer reviews will appear here after they submit them.</p>
                </div>
              ) : (
                <div className="artisan-review-list">
                  {reviews.map((review) => (
                    <article className="artisan-review-card" key={review.id}>
                      <div className="artisan-review-header">
                        <div>
                          <h3>{review.customer_detail?.user?.full_name || 'Customer'}</h3>
                          <p>{review.booking_detail?.service_detail?.name || 'Completed service'}</p>
                        </div>
                        <span className="artisan-review-rating">
                          <i aria-hidden="true" className="bi bi-star-fill" />
                          {Number(review.rating).toFixed(1)}
                        </span>
                      </div>
                      {review.comment && <p className="artisan-review-comment">{review.comment}</p>}
                      <time dateTime={review.created_at}>{formatDate(review.created_at)}</time>
                    </article>
                  ))}
                </div>
              )}
            </section>
          )}
        </>
      )}
    </div>
  )
}
