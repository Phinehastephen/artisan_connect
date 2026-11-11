import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import { apiRequest } from '../api/client'
import CustomerBookings from './CustomerBookings'
import CustomerLocations from './CustomerLocations'
import CustomerProfile from './CustomerProfile'
import './customer-workspace.css'

class LocationAccessError extends Error {}

function getBrowserCoordinates() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new LocationAccessError('Location is not available in this browser.'))
      return
    }

    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve({
        latitude: coords.latitude,
        longitude: coords.longitude,
      }),
      (error) => {
        const messages = {
          1: 'Location permission was denied. Allow location access or choose a saved location.',
          2: 'Your current location could not be determined. Try again or choose a saved location.',
          3: 'Finding your location timed out. Try again or choose a saved location.',
        }
        reject(new LocationAccessError(messages[error.code] || 'Unable to get your current location.'))
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    )
  })
}

function ArtisanMap({ origin, results }) {
  const mapElement = useRef(null)

  useEffect(() => {
    if (!mapElement.current || !origin) return undefined

    const map = L.map(mapElement.current).setView(
      [origin.latitude, origin.longitude],
      11,
    )
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map)

    const points = [L.latLng(origin.latitude, origin.longitude)]
    results.forEach((result) => {
      if (!Number.isFinite(result.latitude) || !Number.isFinite(result.longitude)) return

      const isWorking = result.is_working
      const marker = L.circleMarker([result.latitude, result.longitude], {
        color: isWorking ? '#a12f2f' : '#245b42',
        fillColor: isWorking ? '#c9473d' : '#4b936d',
        fillOpacity: 0.9,
        radius: 8,
        weight: 2,
      }).addTo(map)
      const popup = document.createElement('span')
      popup.textContent = `${result.name} — ${isWorking ? 'Working now' : 'No active Artisan Connect job'}`
      marker.bindPopup(popup)
      points.push(marker.getLatLng())
    })

    if (points.length > 1) {
      map.fitBounds(L.latLngBounds(points).pad(0.15), { maxZoom: 12 })
    }

    return () => map.remove()
  }, [origin, results])

  return (
    <div className="artisan-map-panel">
      <div aria-label="Availability legend" className="availability-legend">
        <span><i className="availability-dot availability-dot-free" /> No active job</span>
        <span><i className="availability-dot availability-dot-working" /> Working now</span>
      </div>
      <div aria-label="Map of matching artisans" className="artisan-map" ref={mapElement} />
      <p className="availability-disclaimer">
        Status reflects active Artisan Connect bookings only. A booking request is not a confirmed appointment.
      </p>
    </div>
  )
}

function formatDistance(distance) {
  return `${Number(distance).toFixed(1)} km away`
}

export default function CustomerWorkspacePage() {
  const [query, setQuery] = useState('')
  const [services, setServices] = useState([])
  const [savedLocations, setSavedLocations] = useState([])
  const [locationType, setLocationType] = useState('current')
  const [locationId, setLocationId] = useState('')
  const [coordinates, setCoordinates] = useState(null)
  const [searchResult, setSearchResult] = useState(null)
  const [scopeQuestions, setScopeQuestions] = useState([])
  const [scopeAnswers, setScopeAnswers] = useState({})
  const [scopeSearchParams, setScopeSearchParams] = useState('')
  const [scopeSubmitted, setScopeSubmitted] = useState(false)
  const [submittingScope, setSubmittingScope] = useState(false)
  const [serviceError, setServiceError] = useState('')
  const [locationError, setLocationError] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingServices, setLoadingServices] = useState(true)
  const [loadingLocations, setLoadingLocations] = useState(true)
  const [activeSection, setActiveSection] = useState('discover')
  const [selectedArtisan, setSelectedArtisan] = useState(null)
  const [selectedBookingService, setSelectedBookingService] = useState(null)
  const [repeatingBooking, setRepeatingBooking] = useState(false)
  const [bookingLocationType, setBookingLocationType] = useState('current')
  const [bookingLocationId, setBookingLocationId] = useState('')
  const [bookingAddress, setBookingAddress] = useState('')
  const [bookingError, setBookingError] = useState('')
  const [bookingSubmitting, setBookingSubmitting] = useState(false)

  useEffect(() => {
    let active = true

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

    apiRequest('/locations/create/locations')
      .then((items) => {
        if (!active) return
        setSavedLocations(items)
        if (items.length) setLocationId(String(items[0].id))
      })
      .catch((requestError) => {
        if (active) setLocationError(requestError.message)
      })
      .finally(() => {
        if (active) setLoadingLocations(false)
      })

    return () => { active = false }
  }, [])

  async function handleLocate() {
    setLocationError('')
    setError('')
    try {
      const currentCoordinates = await getBrowserCoordinates()
      setCoordinates(currentCoordinates)
      setLocationType('current')
    } catch (locationRequestError) {
      setLocationError(locationRequestError.message)
    }
  }

  async function handleSearch(event, requestedQuery = query) {
    event?.preventDefault()
    const trimmedQuery = requestedQuery.trim()
    if (!trimmedQuery) {
      setError('Enter the service you need to search nearby artisans.')
      return
    }

    setQuery(requestedQuery)
    setError('')
    setLocationError('')
    setSearchResult(null)
    setScopeQuestions([])
    setScopeAnswers({})
    setScopeSearchParams('')
    setScopeSubmitted(false)
    setLoading(true)

    try {
      const params = new URLSearchParams({
        q: trimmedQuery,
        location_type: locationType,
      })

      if (locationType === 'saved') {
        if (!locationId) {
          throw new Error('Choose a saved location before searching.')
        }
        params.set('location_id', locationId)
      } else {
        const currentCoordinates = coordinates || await getBrowserCoordinates()
        setCoordinates(currentCoordinates)
        params.set('latitude', String(currentCoordinates.latitude))
        params.set('longitude', String(currentCoordinates.longitude))
      }

      const previewParams = new URLSearchParams(params)
      previewParams.set('resolve_only', 'true')
      const preview = await apiRequest(`/ai/search?${previewParams.toString()}`)
      if (preview.confidence !== 'confident' || !preview.service) {
        setScopeSubmitted(true)
        setSearchResult(preview)
        return
      }

      const questions = await apiRequest(`/services/${preview.service.id}/scope`)
      setScopeQuestions(questions)
      if (questions.length) {
        setScopeSearchParams(params.toString())
        setSearchResult(preview)
        return
      }

      const result = await apiRequest(`/ai/search?${params.toString()}`)
      setScopeSubmitted(true)
      setSearchResult(result)
    } catch (requestError) {
      if (requestError instanceof LocationAccessError) {
        setLocationError(requestError.message)
      } else {
        setError(requestError.message)
      }
    } finally {
      setLoading(false)
    }
  }

  async function submitScopeAnswers(event) {
    event.preventDefault()
    setError('')
    setSubmittingScope(true)
    try {
      const result = await apiRequest(`/ai/search?${scopeSearchParams}`)
      setSearchResult(result)
      setScopeSubmitted(true)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSubmittingScope(false)
    }
  }

  async function handleRepeatBooking(booking) {
    const service = booking.service_detail
    const artisan = booking.artisan_detail
    if (!service?.id || !artisan?.id) {
      throw new Error('This booking does not have enough details to start a repeat request.')
    }
    if (!service.is_active) {
      throw new Error('This service is no longer available for new bookings.')
    }

    const questions = await apiRequest(`/services/${service.id}/scope`)
    const previousAnswers = new Map(
      (booking.scope_answers || []).map((answer) => [answer.key, answer.value]),
    )
    const answers = {}
    questions.forEach((question) => {
      const previousValue = previousAnswers.get(question.key)
      const matchingOption = question.options.find((option) => option.value === previousValue)
      if (matchingOption) answers[question.id] = String(matchingOption.id)
    })

    setError('')
    setBookingError('')
    setSearchResult(null)
    setScopeQuestions(questions)
    setScopeAnswers(answers)
    setScopeSearchParams('')
    setScopeSubmitted(true)
    setSelectedBookingService(service)
    setSelectedArtisan({
      id: artisan.id,
      name: artisan.business_name || artisan.user?.full_name || 'Artisan',
      is_working: false,
    })
    setBookingLocationType(savedLocations.length ? 'saved' : 'current')
    setBookingLocationId(savedLocations[0] ? String(savedLocations[0].id) : '')
    setBookingAddress('')
    setRepeatingBooking(true)
    setActiveSection('discover')
  }

  async function submitBooking(event) {
    event.preventDefault()
    setBookingError('')
    setBookingSubmitting(true)

    try {
      const body = {
        artisan: selectedArtisan.id,
        service: selectedBookingService.id,
        job_location_type: bookingLocationType,
        scope_answers: scopeQuestions.map((question) => ({
          question: question.id,
          option: Number(scopeAnswers[question.id]),
        })),
      }

      if (bookingLocationType === 'saved') {
        if (!bookingLocationId) throw new Error('Choose a saved job location.')
        body.job_location_id = Number(bookingLocationId)
      } else if (bookingLocationType === 'current') {
        const currentCoordinates = await getBrowserCoordinates()
        body.job_latitude = currentCoordinates.latitude
        body.job_longitude = currentCoordinates.longitude
      } else {
        const address = bookingAddress.trim()
        if (address.length < 3) throw new Error('Enter a complete job address.')
        const params = new URLSearchParams({ q: address })
        const places = await apiRequest(`/locations/geocode?${params.toString()}`)
        if (!places.length) throw new Error('No matching address was found. Try adding your area or city.')
        body.job_address = address
        body.job_latitude = places[0].latitude
        body.job_longitude = places[0].longitude
      }

      await apiRequest('/bookings/booking/create', {
        method: 'POST',
        body,
      })
      setSelectedArtisan(null)
      setSelectedBookingService(null)
      setRepeatingBooking(false)
      setBookingAddress('')
      setActiveSection('bookings')
    } catch (requestError) {
      setBookingError(requestError.message)
    } finally {
      setBookingSubmitting(false)
    }
  }

  const suggestions = searchResult?.suggestions || searchResult?.services || []
  const results = searchResult?.results || []

  return (
    <div className="customer-workspace">
      <nav aria-label="Customer workspace" className="customer-workspace-nav">
        <button
          aria-current={activeSection === 'discover' ? 'page' : undefined}
          className={activeSection === 'discover' ? 'active' : ''}
          onClick={() => setActiveSection('discover')}
          type="button"
        >
          <i aria-hidden="true" className="bi bi-compass me-2" />
          Discover artisans
        </button>
        <button
          aria-current={activeSection === 'bookings' ? 'page' : undefined}
          className={activeSection === 'bookings' ? 'active' : ''}
          onClick={() => setActiveSection('bookings')}
          type="button"
        >
          <i aria-hidden="true" className="bi bi-calendar2-check me-2" />
          My bookings
        </button>
        <button
          aria-current={activeSection === 'locations' ? 'page' : undefined}
          className={activeSection === 'locations' ? 'active' : ''}
          onClick={() => setActiveSection('locations')}
          type="button"
        >
          <i aria-hidden="true" className="bi bi-geo-alt me-2" />
          Saved locations
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
      </nav>

      {activeSection === 'bookings' ? <CustomerBookings onRepeatBooking={handleRepeatBooking} />
        : activeSection === 'locations' ? (
          <CustomerLocations
            locations={savedLocations}
            onLocationsChange={setSavedLocations}
          />
        ) : activeSection === 'profile' ? <CustomerProfile /> : (
        <>
      <section aria-labelledby="customer-welcome-title" className="customer-hero">
        <div className="customer-hero-copy">
          <p className="eyebrow">CUSTOMER WORKSPACE</p>
          <h1 id="customer-welcome-title">Find the right artisan for the job.</h1>
          <p className="page-intro">
            Search for a service and discover verified artisans near your location.
          </p>
        </div>

        <form className="discovery-panel" onSubmit={handleSearch}>
          <label className="form-label" htmlFor="artisan-search">
            What service do you need?
          </label>
          <div className="discovery-input-row">
            <i aria-hidden="true" className="bi bi-search" />
            <input
              autoComplete="off"
              className="form-control"
              id="artisan-search"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Try “a leaking kitchen tap”"
              value={query}
            />
            <button className="btn btn-dark" disabled={loading} type="submit">
              {loading ? 'Searching…' : 'Find artisans'}
            </button>
          </div>

          <div className="discovery-location">
            <span className="location-label">
              <i aria-hidden="true" className="bi bi-geo-alt me-1" />
              Search near
            </span>
            <label className="location-choice">
              <input
                checked={locationType === 'current'}
                name="search-location"
                onChange={() => setLocationType('current')}
                type="radio"
              />
              <span>Current location</span>
            </label>
            <label className="location-choice">
              <input
                checked={locationType === 'saved'}
                disabled={!savedLocations.length}
                name="search-location"
                onChange={() => setLocationType('saved')}
                type="radio"
              />
              <span>Saved location</span>
            </label>
            {locationType === 'saved' ? (
              <select
                aria-label="Choose a saved location"
                className="form-select saved-location-select"
                disabled={!savedLocations.length}
                onChange={(event) => setLocationId(event.target.value)}
                value={locationId}
              >
                {savedLocations.map((location) => (
                  <option key={location.id} value={location.id}>{location.name} — {location.address}</option>
                ))}
              </select>
            ) : (
              <button className="current-location-button" onClick={handleLocate} type="button">
                Use my location
              </button>
            )}
            {loadingLocations && <span className="field-note">Loading saved locations…</span>}
          </div>
          {locationError && <p className="field-error mb-0" role="alert">{locationError}</p>}
          {error && <div className="alert alert-danger mt-3 mb-0" role="alert">{error}</div>}
        </form>

        <div className="service-shortcuts">
          <span className="field-note">Popular services</span>
          {loadingServices && <span className="field-note">Loading…</span>}
          {serviceError && <span className="field-error" role="alert">{serviceError}</span>}
          {services.slice(0, 6).map((service) => (
            <button
              className="service-chip"
              key={service.id}
              onClick={() => handleSearch(null, service.name)}
              type="button"
            >
              {service.name}
            </button>
          ))}
        </div>
      </section>

      {searchResult ? (
        <section aria-labelledby="search-results-title" className="search-results">
          <div className="results-heading">
            <div>
              <p className="eyebrow">YOUR SEARCH</p>
              <h2 id="search-results-title">
                {searchResult.confidence === 'confident' && searchResult.service
                  ? searchResult.service.name
                  : 'Refine your search'}
              </h2>
              <p className="page-intro">{searchResult.message}</p>
            </div>
            {searchResult.confidence === 'confident' && scopeSubmitted && (
              <span className="results-count">{results.length} {results.length === 1 ? 'artisan' : 'artisans'}</span>
            )}
          </div>

          {searchResult.confidence === 'confident' && scopeQuestions.length > 0 && !scopeSubmitted && (
            <form className="service-scope-form" onSubmit={submitScopeAnswers}>
              <p className="eyebrow">TELL US ABOUT THE JOB</p>
              <h3>Choose the details that match your request</h3>
              <p className="field-note">
                These structured details help the artisan understand the work. They do not calculate or promise a price.
              </p>
              <div className="service-scope-grid">
                {scopeQuestions.map((question) => (
                  <label className="form-label" htmlFor={`scope-question-${question.id}`} key={question.id}>
                    {question.label}
                    <select
                      className="form-select"
                      id={`scope-question-${question.id}`}
                      onChange={(event) => setScopeAnswers((current) => ({
                        ...current,
                        [question.id]: event.target.value,
                      }))}
                      required
                      value={scopeAnswers[question.id] || ''}
                    >
                      <option disabled value="">Choose an option</option>
                      {question.options.map((option) => (
                        <option key={option.id} value={option.id}>{option.label}</option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
              <button
                className="btn btn-dark"
                disabled={submittingScope || scopeQuestions.some((question) => !scopeAnswers[question.id])}
                type="submit"
              >
                {submittingScope ? 'Finding artisans…' : 'Find artisans'}
              </button>
            </form>
          )}

          {searchResult.confidence === 'confident' && scopeSubmitted && results.length > 0 && (
            <div className="results-layout">
              <div aria-label="Matching artisans" className="artisan-results">
                {results.map((artisan) => (
                  <article className="artisan-card" key={artisan.id}>
                    <div className="artisan-card-heading">
                      <div className="artisan-avatar" aria-hidden="true">
                        {artisan.name?.trim().charAt(0).toUpperCase() || 'A'}
                      </div>
                      <div className="artisan-card-name">
                        <h3>{artisan.name}</h3>
                        {artisan.is_verified && (
                          <span className="verified-label">
                            <i aria-hidden="true" className="bi bi-patch-check-fill" /> Verified artisan
                          </span>
                        )}
                        <span className={`artisan-availability${artisan.is_working ? ' working' : ''}`}>
                          <i aria-hidden="true" className="availability-dot" />
                          {artisan.is_working ? 'Working now' : 'No active Artisan Connect job'}
                        </span>
                      </div>
                      <span className="match-score">{Math.round(artisan.total_score)}<small>/100</small></span>
                    </div>
                    <div className="artisan-card-stats">
                      <span><i aria-hidden="true" className="bi bi-geo-alt" /> {formatDistance(artisan.distance_km)}</span>
                      <span>
                        <i aria-hidden="true" className="bi bi-star-fill rating-star" />
                        {artisan.average_rating ?? 'New'}{artisan.review_count ? ` (${artisan.review_count})` : ''}
                      </span>
                      <span><i aria-hidden="true" className="bi bi-briefcase" /> {artisan.completed_jobs} completed</span>
                    </div>
                    {artisan.location && <p className="artisan-area">{artisan.location}</p>}
                    <button
                      className="btn btn-dark artisan-book-button"
                      onClick={() => {
                        setSelectedArtisan(artisan)
                        setSelectedBookingService(searchResult.service)
                        setRepeatingBooking(false)
                        setBookingLocationType(savedLocations.length ? 'saved' : 'current')
                        setBookingLocationId(savedLocations[0] ? String(savedLocations[0].id) : '')
                        setBookingError('')
                      }}
                      type="button"
                    >
                      Request booking
                      <i aria-hidden="true" className="bi bi-arrow-right ms-2" />
                    </button>
                  </article>
                ))}
              </div>
              <ArtisanMap origin={searchResult.origin} results={results} />
            </div>
          )}

          {searchResult.confidence === 'confident' && scopeSubmitted && results.length === 0 && (
            <div className="empty-results">
              <i aria-hidden="true" className="bi bi-geo-alt" />
              <h3>No matching artisans nearby yet</h3>
              <p>Try a different saved location or check back later.</p>
            </div>
          )}

          {searchResult.confidence !== 'confident' && suggestions.length > 0 && (
            <div aria-label="Suggested services" className="suggestion-grid">
              {suggestions.map((service) => (
                <button
                  className="suggestion-card"
                  key={service.id}
                  onClick={() => handleSearch(null, service.name)}
                  type="button"
                >
                  <span className="suggestion-icon"><i aria-hidden="true" className="bi bi-tools" /></span>
                  <span>{service.name}</span>
                  <i aria-hidden="true" className="bi bi-arrow-up-right" />
                </button>
              ))}
            </div>
          )}
        </section>
      ) : (
        <section aria-label="How discovery works" className="discovery-note">
          <div className="discovery-note-icon"><i aria-hidden="true" className="bi bi-shield-check" /></div>
          <div>
            <h2>Local search, with trust built in.</h2>
            <p>
              Results show verified artisans offering the service you need, ranked by
              reviews, experience, distance, and response time.
            </p>
          </div>
        </section>
      )}
        </>
      )}
      {selectedArtisan && (
        <div className="booking-dialog-backdrop">
          <section
            aria-labelledby="booking-dialog-title"
            aria-modal="true"
            className="booking-dialog"
            role="dialog"
          >
            <button
              aria-label="Close booking request"
              className="booking-dialog-close"
              onClick={() => setSelectedArtisan(null)}
              type="button"
            >
              <i aria-hidden="true" className="bi bi-x-lg" />
            </button>
            <p className="eyebrow">{repeatingBooking ? 'REPEAT REQUEST' : 'NEW REQUEST'}</p>
            <h2 id="booking-dialog-title">{repeatingBooking ? 'Book this artisan again' : 'Request a booking'}</h2>
            <p className="booking-dialog-summary">
              {selectedBookingService.name} with {selectedArtisan.name}
            </p>
            {scopeQuestions.length > 0 && (
              repeatingBooking ? (
                <div className="service-scope-grid booking-repeat-scope">
                  {scopeQuestions.map((question) => (
                    <label className="form-label" htmlFor={`repeat-scope-${question.id}`} key={question.id}>
                      {question.label}
                      <select
                        className="form-select"
                        id={`repeat-scope-${question.id}`}
                        onChange={(event) => setScopeAnswers((current) => ({
                          ...current,
                          [question.id]: event.target.value,
                        }))}
                        required
                        value={scopeAnswers[question.id] || ''}
                      >
                        <option disabled value="">Choose an option</option>
                        {question.options.map((option) => (
                          <option key={option.id} value={option.id}>{option.label}</option>
                        ))}
                      </select>
                    </label>
                  ))}
                </div>
              ) : (
                <dl className="booking-scope-summary">
                  {scopeQuestions.map((question) => {
                    const selectedOption = question.options.find(
                      (option) => String(option.id) === String(scopeAnswers[question.id]),
                    )
                    return (
                      <div key={question.id}>
                        <dt>{question.label}</dt>
                        <dd>{selectedOption?.label || 'Not selected'}</dd>
                      </div>
                    )
                  })}
                </dl>
              )
            )}
            {repeatingBooking && (
              <p className="field-note">
                Review the job details and choose where the new job will take place. This sends a new request; it does not change your previous booking.
              </p>
            )}
            {selectedArtisan.is_working && (
              <p className="booking-working-note">
                This artisan is marked as working on another Artisan Connect job. You can still send a request; the artisan must accept it.
              </p>
            )}
            {bookingError && <div className="alert alert-danger" role="alert">{bookingError}</div>}
            <form className="booking-dialog-form" onSubmit={submitBooking}>
              <fieldset>
                <legend>Where is the job?</legend>
                {savedLocations.length > 0 && (
                  <label className="booking-location-option">
                    <input
                      checked={bookingLocationType === 'saved'}
                      name="booking-location"
                      onChange={() => setBookingLocationType('saved')}
                      type="radio"
                    />
                    Use a saved location
                  </label>
                )}
                <label className="booking-location-option">
                  <input
                    checked={bookingLocationType === 'current'}
                    name="booking-location"
                    onChange={() => setBookingLocationType('current')}
                    type="radio"
                  />
                  Use my current location
                </label>
                <label className="booking-location-option">
                  <input
                    checked={bookingLocationType === 'custom'}
                    name="booking-location"
                    onChange={() => setBookingLocationType('custom')}
                    type="radio"
                  />
                  Enter an address
                </label>
              </fieldset>

              {bookingLocationType === 'saved' && (
                <div className="mb-3">
                  <label className="form-label" htmlFor="booking-saved-location">Saved location</label>
                  <select
                    className="form-select"
                    id="booking-saved-location"
                    onChange={(event) => setBookingLocationId(event.target.value)}
                    required
                    value={bookingLocationId}
                  >
                    {savedLocations.map((location) => (
                      <option key={location.id} value={location.id}>
                        {location.name} — {location.address}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              {bookingLocationType === 'current' && (
                <p className="field-note">
                  Your browser will ask permission to share the job location. The address is visible only to you and the assigned artisan after acceptance.
                </p>
              )}
              {bookingLocationType === 'custom' && (
                <div className="mb-3">
                  <label className="form-label" htmlFor="booking-custom-address">Job address</label>
                  <input
                    autoComplete="street-address"
                    className="form-control"
                    id="booking-custom-address"
                    minLength={3}
                    onChange={(event) => setBookingAddress(event.target.value)}
                    placeholder="Street, area, city"
                    required
                    value={bookingAddress}
                  />
                </div>
              )}
              <div className="booking-dialog-actions">
                <button className="btn btn-outline-dark" onClick={() => setSelectedArtisan(null)} type="button">
                  Go back
                </button>
                <button className="btn btn-dark" disabled={bookingSubmitting} type="submit">
                  {bookingSubmitting ? 'Sending request…' : repeatingBooking ? 'Send repeat request' : 'Send booking request'}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  )
}
