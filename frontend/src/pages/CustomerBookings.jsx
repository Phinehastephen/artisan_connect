import { useEffect, useState } from 'react'
import { apiRequest } from '../api/client'

const cancellableStatuses = ['PENDING', 'ACCEPTED']

function formatDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function artisanName(booking) {
  return booking.artisan_detail?.business_name
    || booking.artisan_detail?.user?.full_name
    || 'Artisan'
}

export default function CustomerBookings() {
  const [bookings, setBookings] = useState([])
  const [loading, setLoading] = useState(true)
  const [submittingId, setSubmittingId] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [disputeId, setDisputeId] = useState(null)
  const [disputeReason, setDisputeReason] = useState('')
  const [reviewDrafts, setReviewDrafts] = useState({})
  const [reviewSubmittingId, setReviewSubmittingId] = useState(null)

  useEffect(() => {
    let active = true
    apiRequest('/bookings/list')
      .then((items) => {
        if (active) setBookings(items)
      })
      .catch((requestError) => {
        if (active) setError(requestError.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => { active = false }
  }, [])

  async function loadBookings() {
    setLoading(true)
    setError('')
    try {
      const items = await apiRequest('/bookings/list')
      setBookings(items)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  async function runAction(booking, action, body = undefined) {
    setError('')
    setNotice('')
    setSubmittingId(booking.id)
    try {
      const updatedBooking = await apiRequest(
        `/bookings/status/${booking.id}/${action}`,
        { method: 'POST', body },
      )
      setBookings((current) => current.map((item) => (
        item.id === updatedBooking.id ? updatedBooking : item
      )))
      setDisputeId(null)
      setDisputeReason('')
      setNotice(`Booking #${booking.id} updated.`)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSubmittingId(null)
    }
  }

  function submitDispute(event, booking) {
    event.preventDefault()
    if (disputeReason.trim().length < 20) {
      setError('Please explain why the job is not done (at least 20 characters).')
      return
    }
    runAction(booking, 'disagree', { reason: disputeReason })
  }

  async function submitReview(event, booking) {
    event.preventDefault()
    const draft = reviewDrafts[booking.id] || { rating: '5', comment: '' }
    setError('')
    setNotice('')
    setReviewSubmittingId(booking.id)
    try {
      await apiRequest('/reviews/review/create', {
        method: 'POST',
        body: {
          booking: booking.id,
          rating: Number(draft.rating),
          comment: draft.comment,
        },
      })
      setBookings((current) => current.map((item) => (
        item.id === booking.id ? { ...item, has_review: true } : item
      )))
      setNotice(`Your review for booking #${booking.id} was submitted.`)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setReviewSubmittingId(null)
    }
  }

  return (
    <section aria-labelledby="bookings-title" className="customer-bookings">
      <div className="results-heading">
        <div>
          <p className="eyebrow">YOUR ACTIVITY</p>
          <h2 id="bookings-title">Your bookings</h2>
          <p className="page-intro">Track requests and manage completed work.</p>
        </div>
        <button
          aria-label="Refresh bookings"
          className="btn btn-outline-dark booking-refresh"
          disabled={loading}
          onClick={loadBookings}
          type="button"
        >
          <i aria-hidden="true" className="bi bi-arrow-clockwise me-1" />
          Refresh
        </button>
      </div>

      <p className="booking-payment-note">
        <i aria-hidden="true" className="bi bi-info-circle me-1" />
        Payments are not handled here. Booking status and payment status are separate.
      </p>

      {notice && <div className="alert alert-success" role="status">{notice}</div>}
      {error && <div className="alert alert-danger" role="alert">{error}</div>}

      {loading ? (
        <p aria-live="polite" className="booking-loading" role="status">Loading your bookings…</p>
      ) : bookings.length === 0 ? (
        <div className="empty-results">
          <i aria-hidden="true" className="bi bi-calendar2-check" />
          <h3>No bookings yet</h3>
          <p>Your booking requests and updates will appear here.</p>
        </div>
      ) : (
        <div className="booking-list">
          {bookings.map((booking) => {
            const isSubmitting = submittingId === booking.id
            const serviceName = booking.service_detail?.name || 'Service'

            return (
              <article className="booking-card" key={booking.id}>
                <div className="booking-card-top">
                  <div>
                    <p className="booking-reference">BOOKING {booking.id}</p>
                    <h3>{serviceName}</h3>
                    <p className="booking-artisan">with {artisanName(booking)}</p>
                  </div>
                  <span className={`booking-status status-${booking.status.toLowerCase()}`}>
                    {booking.status.replaceAll('_', ' ')}
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
                  {booking.finalization_method && (
                    <div>
                      <dt>Completion</dt>
                      <dd>{booking.finalization_method.replaceAll('_', ' ')}</dd>
                    </div>
                  )}
                  {booking.status === 'DISPUTED' && (
                    <div className="booking-dispute-detail">
                      <dt>Dispute submitted</dt>
                      <dd>{booking.dispute_reason}</dd>
                    </div>
                  )}
                </dl>

                {booking.status === 'COMPLETED' && (
                  <div className="booking-confirm-panel">
                    <p>The artisan marked this job complete. Confirm if the work is finished, or report a problem.</p>
                    <div className="booking-actions">
                      <button
                        className="btn btn-success"
                        disabled={isSubmitting}
                        onClick={() => runAction(booking, 'confirm')}
                        type="button"
                      >
                        {isSubmitting ? 'Updating…' : 'Confirm completion'}
                      </button>
                      <button
                        className="btn btn-outline-dark"
                        disabled={isSubmitting}
                        onClick={() => {
                          setDisputeId(disputeId === booking.id ? null : booking.id)
                          setDisputeReason('')
                          setError('')
                        }}
                        type="button"
                      >
                        Report a problem
                      </button>
                    </div>
                    {disputeId === booking.id && (
                      <form className="dispute-form" onSubmit={(event) => submitDispute(event, booking)}>
                        <label className="form-label" htmlFor={`dispute-reason-${booking.id}`}>
                          Explain what is still unresolved (at least 20 characters)
                        </label>
                        <textarea
                          className="form-control"
                          id={`dispute-reason-${booking.id}`}
                          maxLength={2000}
                          minLength={20}
                          onChange={(event) => setDisputeReason(event.target.value)}
                          required
                          rows={3}
                          value={disputeReason}
                        />
                        <button className="btn btn-danger mt-2" disabled={isSubmitting} type="submit">
                          Submit dispute
                        </button>
                      </form>
                    )}
                  </div>
                )}

                {booking.status === 'DISPUTED' && (
                  <p className="booking-follow-up">
                    Your dispute is awaiting admin review. The booking team will update this status when it is resolved.
                  </p>
                )}

                {booking.status === 'FINALIZED' && booking.has_review && (
                  <p className="review-submitted">
                    <i aria-hidden="true" className="bi bi-check-circle-fill me-1" />
                    You’ve reviewed this booking.
                  </p>
                )}

                {booking.status === 'FINALIZED' && !booking.has_review && (
                  <form className="booking-review-form" onSubmit={(event) => submitReview(event, booking)}>
                    <h4>How was the service?</h4>
                    <div className="row g-3">
                      <div className="col-12 col-sm-4">
                        <label className="form-label" htmlFor={`review-rating-${booking.id}`}>Rating</label>
                        <select
                          className="form-select"
                          id={`review-rating-${booking.id}`}
                          onChange={(event) => setReviewDrafts((current) => ({
                            ...current,
                            [booking.id]: {
                              ...current[booking.id],
                              rating: event.target.value,
                            },
                          }))}
                          value={reviewDrafts[booking.id]?.rating || '5'}
                        >
                          {[5, 4, 3, 2, 1].map((rating) => (
                            <option key={rating} value={rating}>{rating} {rating === 1 ? 'star' : 'stars'}</option>
                          ))}
                        </select>
                      </div>
                      <div className="col-12 col-sm-8">
                        <label className="form-label" htmlFor={`review-comment-${booking.id}`}>
                          Comment <span>(optional)</span>
                        </label>
                        <textarea
                          className="form-control"
                          id={`review-comment-${booking.id}`}
                          maxLength={2000}
                          onChange={(event) => setReviewDrafts((current) => ({
                            ...current,
                            [booking.id]: {
                              ...current[booking.id],
                              comment: event.target.value,
                            },
                          }))}
                          rows={2}
                          value={reviewDrafts[booking.id]?.comment || ''}
                        />
                      </div>
                    </div>
                    <button
                      className="btn btn-dark mt-3"
                      disabled={reviewSubmittingId === booking.id}
                      type="submit"
                    >
                      {reviewSubmittingId === booking.id ? 'Submitting…' : 'Submit review'}
                    </button>
                  </form>
                )}

                {cancellableStatuses.includes(booking.status) && (
                  <div className="booking-actions booking-cancel-row">
                    <button
                      className="btn btn-outline-danger"
                      disabled={isSubmitting}
                      onClick={() => runAction(booking, 'cancel')}
                      type="button"
                    >
                      {isSubmitting ? 'Updating…' : 'Cancel booking'}
                    </button>
                  </div>
                )}
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
