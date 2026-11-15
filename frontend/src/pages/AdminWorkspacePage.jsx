import { useEffect, useState } from 'react'
import { apiRequest, tokenStorage } from '../api/client'
import './admin-workspace.css'

const sections = [
  { id: 'artisans', label: 'Artisan verification', icon: 'bi-person-check' },
  { id: 'services', label: 'Service changes', icon: 'bi-tools' },
  { id: 'disputes', label: 'Booking disputes', icon: 'bi-exclamation-triangle' },
]

function formatDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function artisanName(artisan) {
  return artisan.business_name || artisan.user?.full_name || artisan.user?.username || `Artisan #${artisan.id}`
}

function bookingPartyName(booking, party) {
  const detail = booking[`${party}_detail`]
  return detail?.business_name || detail?.user?.full_name || `${party} #${booking[party]}`
}

function fetchReviewQueues() {
  return Promise.all([
    apiRequest('/artisans/pending'),
    apiRequest('/artisans/service-change-requests'),
    apiRequest('/bookings/list'),
    apiRequest('/artisans/artisan'),
    apiRequest('/artisans/rejected'),
  ])
}

async function downloadEvidence(evidence) {
  const response = await fetch(evidence.download_url, {
    headers: {
      Authorization: `Bearer ${tokenStorage.getAccessToken()}`,
    },
  })

  if (!response.ok) {
    let message = 'Could not download qualification evidence.'
    try {
      const data = await response.json()
      message = data.detail || data.error || message
    } catch {
      // Keep the actionable fallback when the server does not return JSON.
    }
    throw new Error(message)
  }

  const blobUrl = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = blobUrl
  anchor.download = `qualification-evidence-${evidence.id}`
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(blobUrl)
}

function QueueState({ loading, error, empty, children }) {
  if (loading) {
    return <p aria-live="polite" className="admin-queue-state" role="status">Loading review queue…</p>
  }
  if (error) {
    return <div className="alert alert-danger" role="alert">{error}</div>
  }
  if (empty) {
    return (
      <div className="admin-empty-state">
        <i aria-hidden="true" className="bi bi-check2-circle" />
        <h3>Queue is clear</h3>
        <p>There are no items waiting for review.</p>
      </div>
    )
  }
  return children
}

export default function AdminWorkspacePage() {
  const [activeSection, setActiveSection] = useState('artisans')
  const [pendingArtisans, setPendingArtisans] = useState([])
  const [serviceRequests, setServiceRequests] = useState([])
  const [disputedBookings, setDisputedBookings] = useState([])
  const [verifiedArtisans, setVerifiedArtisans] = useState([])
  const [totalArtisanCount, setTotalArtisanCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [actionId, setActionId] = useState(null)
  const [downloadId, setDownloadId] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function loadReviewQueues() {
    setError('')
    setLoading(true)
    try {
      const [artisans, requests, bookings, verified, rejected] = await fetchReviewQueues()
      setPendingArtisans(artisans)
      setServiceRequests(requests.filter((request) => request.status === 'PENDING'))
      setDisputedBookings(bookings.filter((booking) => booking.status === 'DISPUTED'))
      setVerifiedArtisans(verified)
      setTotalArtisanCount(artisans.length + verified.length + rejected.length)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    fetchReviewQueues()
      .then(([artisans, requests, bookings, verified, rejected]) => {
        if (!active) return
        setPendingArtisans(artisans)
        setServiceRequests(requests.filter((request) => request.status === 'PENDING'))
        setDisputedBookings(bookings.filter((booking) => booking.status === 'DISPUTED'))
        setVerifiedArtisans(verified)
        setTotalArtisanCount(artisans.length + verified.length + rejected.length)
      })
      .catch((requestError) => {
        if (active) setError(requestError.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [])

  async function runDecision(id, action, endpoint, queueKey) {
    const prompts = {
      approve: 'Approve this application?',
      reject: 'Reject this request? This decision will be applied immediately.',
      finalize: 'Finalize this disputed booking? This closes the dispute.',
      reopen: 'Reopen this booking? Work will return to the artisan.',
    }
    if (!window.confirm(prompts[action])) return

    setActionId(`${queueKey}-${id}`)
    setError('')
    setNotice('')
    try {
      const response = await apiRequest(endpoint(id, action), { method: 'POST' })
      setNotice(response.message || 'Decision saved.')
      await loadReviewQueues()
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setActionId(null)
    }
  }

  async function handleEvidenceDownload(evidence) {
    setDownloadId(evidence.id)
    setError('')
    try {
      await downloadEvidence(evidence)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setDownloadId(null)
    }
  }

  const pendingCount = pendingArtisans.length
    + serviceRequests.length
    + disputedBookings.length

  return (
    <div className="admin-workspace">
      <header className="admin-welcome">
        <div>
          <p className="eyebrow">ADMINISTRATION</p>
          <h1>Review and resolve</h1>
          <p className="page-intro">
            Verify artisan accounts, review service changes, and settle booking disputes.
          </p>
        </div>
        <div className="admin-summary-cards">
          <div aria-label={`${pendingCount} items need review`} className="admin-pending-summary">
            <strong>{pendingCount}</strong>
            <span>{pendingCount === 1 ? 'item needs review' : 'items need review'}</span>
          </div>
          <div aria-label={`${totalArtisanCount} artisans on the system`} className="admin-artisan-total">
            <strong>{totalArtisanCount}</strong>
            <span>Total artisans</span>
          </div>
        </div>
      </header>

      <nav aria-label="Admin review queues" className="admin-workspace-nav">
        {sections.map((section) => {
          const count = section.id === 'artisans'
            ? pendingArtisans.length
            : section.id === 'services'
              ? serviceRequests.length
              : disputedBookings.length
          return (
            <button
              aria-current={activeSection === section.id ? 'page' : undefined}
              className={activeSection === section.id ? 'active' : ''}
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              type="button"
            >
              <i aria-hidden="true" className={`bi ${section.icon} me-2`} />
              {section.label}
              {count > 0 && <span className="admin-nav-count">{count}</span>}
            </button>
          )
        })}
      </nav>

      <div className="admin-queue-toolbar">
        <p className="field-note mb-0">Review submitted information before making a decision.</p>
        <button
          className="btn btn-sm btn-outline-dark"
          disabled={loading}
          onClick={() => void loadReviewQueues()}
          type="button"
        >
          <i aria-hidden="true" className="bi bi-arrow-clockwise me-1" />
          Refresh
        </button>
      </div>

      {notice && <div className="alert alert-success" role="status">{notice}</div>}

      <QueueState loading={loading} error={error} empty={false}>
        {activeSection === 'artisans' && (
          <section aria-labelledby="admin-artisan-queue-title" className="admin-queue">
            <div className="admin-queue-heading">
              <div>
                <p className="eyebrow">ACCOUNT APPROVAL</p>
                <h2 id="admin-artisan-queue-title">Pending artisan verification</h2>
              </div>
              <span className="admin-queue-total">{pendingArtisans.length} pending</span>
            </div>
            {pendingArtisans.length === 0 ? (
              <div className="admin-empty-state">
                <i aria-hidden="true" className="bi bi-check2-circle" />
                <h3>No artisans awaiting verification</h3>
                <p>New artisan applications will appear here.</p>
              </div>
            ) : (
              <div className="admin-review-list">
                {pendingArtisans.map((artisan) => (
                  <article className="admin-review-card" key={artisan.id}>
                    <div className="admin-review-card-heading">
                      <div>
                        <p className="admin-record-reference">ARTISAN #{artisan.id}</p>
                        <h3>{artisanName(artisan)}</h3>
                        <p>{artisan.user?.email}</p>
                      </div>
                      <span className="admin-review-status">Pending</span>
                    </div>
                    <dl className="admin-review-details">
                      <div><dt>Phone</dt><dd>{artisan.phone_number || 'Not provided'}</dd></div>
                      <div><dt>Business</dt><dd>{artisan.business_name || 'Not provided'}</dd></div>
                      <div><dt>Service area</dt><dd>{artisan.default_location || 'Not provided'}</dd></div>
                      <div><dt>Applied</dt><dd>{formatDate(artisan.created_at)}</dd></div>
                      <div className="admin-review-services">
                        <dt>Offered services</dt>
                        <dd>{artisan.services?.length ? artisan.services.map((service) => service.name).join(', ') : 'None listed'}</dd>
                      </div>
                    </dl>
                    <div className="admin-review-actions">
                      <button
                        className="btn btn-success"
                        disabled={actionId === `artisan-${artisan.id}`}
                        onClick={() => void runDecision(
                          artisan.id,
                          'approve',
                          (id, action) => `/artisans/verification/${id}/${action}`,
                          'artisan',
                        )}
                        type="button"
                      >
                        Approve artisan
                      </button>
                      <button
                        className="btn btn-outline-danger"
                        disabled={actionId === `artisan-${artisan.id}`}
                        onClick={() => void runDecision(
                          artisan.id,
                          'reject',
                          (id, action) => `/artisans/verification/${id}/${action}`,
                          'artisan',
                        )}
                        type="button"
                      >
                        Reject artisan
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        )}

        {activeSection === 'services' && (
          <section aria-labelledby="admin-service-queue-title" className="admin-queue">
            <div className="admin-queue-heading">
              <div>
                <p className="eyebrow">SERVICE REVIEW</p>
                <h2 id="admin-service-queue-title">Pending service change requests</h2>
              </div>
              <span className="admin-queue-total">{serviceRequests.length} pending</span>
            </div>
            {serviceRequests.length === 0 ? (
              <div className="admin-empty-state">
                <i aria-hidden="true" className="bi bi-check2-circle" />
                <h3>No service changes awaiting review</h3>
                <p>Submitted replacement service lists will appear here.</p>
              </div>
            ) : (
              <div className="admin-review-list">
                {serviceRequests.map((request) => (
                  <article className="admin-review-card" key={request.id}>
                    <div className="admin-review-card-heading">
                      <div>
                        <p className="admin-record-reference">REQUEST #{request.id}</p>
                        <h3>
                          {artisanName(verifiedArtisans.find((artisan) => artisan.id === request.artisan)
                            || { id: request.artisan })}
                        </h3>
                        <p>Submitted {formatDate(request.created_at)}</p>
                      </div>
                      <span className="admin-review-status">Pending</span>
                    </div>
                    <div className="admin-review-details admin-service-review-details">
                      <div>
                        <strong>Proposed complete service list</strong>
                        <p>{request.services?.map((service) => service.name).join(', ') || 'No services listed'}</p>
                      </div>
                      <div>
                        <strong>Reason</strong>
                        <p>{request.reason}</p>
                      </div>
                    </div>
                    <div className="admin-evidence-list">
                      <strong>Qualification evidence</strong>
                      {request.qualification_evidence?.length ? request.qualification_evidence.map((evidence) => (
                        <button
                          className="btn btn-sm btn-outline-dark"
                          disabled={downloadId === evidence.id}
                          key={evidence.id}
                          onClick={() => void handleEvidenceDownload(evidence)}
                          type="button"
                        >
                          <i aria-hidden="true" className="bi bi-download me-1" />
                          {downloadId === evidence.id ? 'Downloading…' : `${evidence.category.replaceAll('_', ' ')} evidence`}
                        </button>
                      )) : <p className="field-note">No evidence attached.</p>}
                    </div>
                    <div className="admin-review-actions">
                      <button
                        className="btn btn-success"
                        disabled={actionId === `service-${request.id}`}
                        onClick={() => void runDecision(
                          request.id,
                          'approve',
                          (id, action) => `/artisans/service-change-requests/${id}/${action}`,
                          'service',
                        )}
                        type="button"
                      >
                        Approve service change
                      </button>
                      <button
                        className="btn btn-outline-danger"
                        disabled={actionId === `service-${request.id}`}
                        onClick={() => void runDecision(
                          request.id,
                          'reject',
                          (id, action) => `/artisans/service-change-requests/${id}/${action}`,
                          'service',
                        )}
                        type="button"
                      >
                        Reject service change
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        )}

        {activeSection === 'disputes' && (
          <section aria-labelledby="admin-dispute-queue-title" className="admin-queue">
            <div className="admin-queue-heading">
              <div>
                <p className="eyebrow">BOOKING RESOLUTION</p>
                <h2 id="admin-dispute-queue-title">Disputed bookings</h2>
              </div>
              <span className="admin-queue-total">{disputedBookings.length} open</span>
            </div>
            {disputedBookings.length === 0 ? (
              <div className="admin-empty-state">
                <i aria-hidden="true" className="bi bi-check2-circle" />
                <h3>No disputed bookings</h3>
                <p>Customer disputes requiring an admin decision will appear here.</p>
              </div>
            ) : (
              <div className="admin-review-list">
                {disputedBookings.map((booking) => (
                  <article className="admin-review-card" key={booking.id}>
                    <div className="admin-review-card-heading">
                      <div>
                        <p className="admin-record-reference">BOOKING #{booking.id}</p>
                        <h3>{booking.service_detail?.name || 'Service'}</h3>
                        <p>Disputed {formatDate(booking.disputed_at)}</p>
                      </div>
                      <span className="admin-review-status admin-review-status-disputed">Disputed</span>
                    </div>
                    <dl className="admin-review-details">
                      <div><dt>Customer</dt><dd>{bookingPartyName(booking, 'customer')}</dd></div>
                      <div><dt>Artisan</dt><dd>{bookingPartyName(booking, 'artisan')}</dd></div>
                      <div><dt>Job location</dt><dd>{booking.job_address || 'No longer available'}</dd></div>
                      <div className="admin-review-services">
                        <dt>Customer's reason</dt>
                        <dd>{booking.dispute_reason || 'No reason provided.'}</dd>
                      </div>
                      {booking.scope_answers?.length > 0 && (
                        <div className="admin-review-services">
                          <dt>Recorded job details</dt>
                          <dd>{booking.scope_answers.map((answer) => `${answer.question}: ${answer.answer}`).join(' · ')}</dd>
                        </div>
                      )}
                    </dl>
                    <div className="admin-review-actions">
                      <button
                        className="btn btn-success"
                        disabled={actionId === `booking-${booking.id}`}
                        onClick={() => void runDecision(
                          booking.id,
                          'finalize',
                          (id, action) => `/bookings/status/${id}/${action}`,
                          'booking',
                        )}
                        type="button"
                      >
                        Finalize dispute
                      </button>
                      <button
                        className="btn btn-outline-dark"
                        disabled={actionId === `booking-${booking.id}`}
                        onClick={() => void runDecision(
                          booking.id,
                          'reopen',
                          (id, action) => `/bookings/status/${id}/${action}`,
                          'booking',
                        )}
                        type="button"
                      >
                        Reopen work
                      </button>
                    </div>
                    <p className="admin-review-caution">
                      Finalizing closes the dispute. Reopening returns the booking to the artisan to continue the work.
                    </p>
                  </article>
                ))}
              </div>
            )}
          </section>
        )}
      </QueueState>
    </div>
  )
}
