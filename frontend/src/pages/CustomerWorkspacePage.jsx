import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import { apiRequest } from '../api/client'
import CustomerBookings from './CustomerBookings'
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

      const marker = L.circleMarker([result.latitude, result.longitude], {
        color: '#245b42',
        fillColor: '#4b936d',
        fillOpacity: 0.9,
        radius: 8,
        weight: 2,
      }).addTo(map)
      const popup = document.createElement('span')
      popup.textContent = result.name
      marker.bindPopup(popup)
      points.push(marker.getLatLng())
    })

    if (points.length > 1) {
      map.fitBounds(L.latLngBounds(points).pad(0.15), { maxZoom: 12 })
    }

    return () => map.remove()
  }, [origin, results])

  return <div aria-label="Map of matching artisans" className="artisan-map" ref={mapElement} />
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
  const [serviceError, setServiceError] = useState('')
  const [locationError, setLocationError] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingServices, setLoadingServices] = useState(true)
  const [loadingLocations, setLoadingLocations] = useState(true)
  const [activeSection, setActiveSection] = useState('discover')

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

      const result = await apiRequest(`/ai/search?${params.toString()}`)
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
      </nav>

      {activeSection === 'bookings' ? <CustomerBookings /> : (
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
            {searchResult.confidence === 'confident' && (
              <span className="results-count">{results.length} {results.length === 1 ? 'artisan' : 'artisans'}</span>
            )}
          </div>

          {searchResult.confidence === 'confident' && results.length > 0 && (
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
                  </article>
                ))}
              </div>
              <ArtisanMap origin={searchResult.origin} results={results} />
            </div>
          )}

          {searchResult.confidence === 'confident' && results.length === 0 && (
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
    </div>
  )
}
