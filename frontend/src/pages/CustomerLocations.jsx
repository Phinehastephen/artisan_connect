import { useState } from 'react'
import { apiRequest } from '../api/client'

const emptyForm = { name: '', address: '' }

export default function CustomerLocations({ locations, onLocationsChange }) {
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [addressMatches, setAddressMatches] = useState([])
  const [selectedMatch, setSelectedMatch] = useState(null)

  function startEdit(location) {
    setEditingId(location.id)
    setForm({ name: location.name, address: location.address })
    setAddressMatches([])
    setSelectedMatch(null)
    setError('')
    setNotice('')
  }

  function resetForm() {
    setEditingId(null)
    setForm(emptyForm)
    setAddressMatches([])
    setSelectedMatch(null)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setNotice('')
    setSubmitting(true)

    try {
      if (!selectedMatch) {
        const geocodeParams = new URLSearchParams({ q: form.address.trim() })
        const matches = await apiRequest(`/locations/geocode?${geocodeParams.toString()}`)
        if (!matches.length) {
          throw new Error('No matching address found. Add an area or city and try again.')
        }
        setAddressMatches(matches)
        return
      }

      const locationData = {
        name: form.name.trim(),
        address: selectedMatch.display_name,
        latitude: selectedMatch.latitude,
        longitude: selectedMatch.longitude,
      }
      const savedLocation = editingId
        ? await apiRequest(`/locations/saved/details/${editingId}`, {
          method: 'PATCH',
          body: locationData,
        })
        : await apiRequest('/locations/create/locations', {
          method: 'POST',
          body: locationData,
        })

      onLocationsChange((current) => editingId
        ? current.map((location) => location.id === editingId ? savedLocation : location)
        : [savedLocation, ...current])
      setNotice(editingId ? 'Saved location updated.' : 'Saved location added.')
      resetForm()
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function deleteLocation(location) {
    setError('')
    setNotice('')
    setDeletingId(location.id)
    try {
      await apiRequest(`/locations/saved/details/${location.id}`, { method: 'DELETE' })
      onLocationsChange((current) => current.filter((item) => item.id !== location.id))
      if (editingId === location.id) resetForm()
      setNotice(`${location.name} removed from your saved locations.`)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <section aria-labelledby="saved-locations-title" className="customer-locations">
      <div className="results-heading">
        <div>
          <p className="eyebrow">YOUR PLACES</p>
          <h2 id="saved-locations-title">Saved locations</h2>
          <p className="page-intro">Save up to five places for faster artisan searches and booking requests.</p>
        </div>
        <span className="results-count">{locations.length} / 5 saved</span>
      </div>

      {notice && <div className="alert alert-success" role="status">{notice}</div>}
      {error && <div className="alert alert-danger" role="alert">{error}</div>}

      <form className="saved-location-form" onSubmit={handleSubmit}>
        <h3>{editingId ? 'Edit location' : 'Add a location'}</h3>
        <p className="field-note">
          We’ll look up the address. Choose the matching place before saving its map coordinates.
        </p>
        <div className="row g-3">
          <div className="col-12 col-md-4">
            <label className="form-label" htmlFor="saved-location-name">Location name</label>
            <input
              className="form-control"
              id="saved-location-name"
              maxLength={50}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              placeholder="Home, office…"
              required
              value={form.name}
            />
          </div>
          <div className="col-12 col-md-8">
            <label className="form-label" htmlFor="saved-location-address">Address</label>
            <input
              autoComplete="street-address"
              className="form-control"
              id="saved-location-address"
              maxLength={255}
              minLength={3}
              onChange={(event) => {
                setForm({ ...form, address: event.target.value })
                setAddressMatches([])
                setSelectedMatch(null)
              }}
              placeholder="Street, area, city"
              required
              value={form.address}
            />
          </div>
        </div>
        {addressMatches.length > 0 && (
          <fieldset className="saved-location-matches">
            <legend>Choose the matching address</legend>
            {addressMatches.map((match, index) => {
              const value = `${match.latitude},${match.longitude}`
              return (
                <label className="saved-location-match" key={`${value}-${index}`}>
                  <input
                    checked={selectedMatch?.latitude === match.latitude
                      && selectedMatch?.longitude === match.longitude}
                    name="saved-location-match"
                    onChange={() => setSelectedMatch(match)}
                    type="radio"
                  />
                  <span>{match.display_name}</span>
                </label>
              )
            })}
          </fieldset>
        )}
        <div className="saved-location-form-actions">
          {editingId && (
            <button className="btn btn-outline-dark" onClick={resetForm} type="button">
              Stop editing
            </button>
          )}
          <button
            className="btn btn-dark"
            disabled={submitting || (!editingId && locations.length >= 5)}
            type="submit"
          >
            {submitting
              ? selectedMatch ? 'Saving…' : 'Finding address…'
              : selectedMatch
                ? editingId ? 'Save changes' : 'Add saved location'
                : 'Find address'}
          </button>
        </div>
        {!editingId && locations.length >= 5 && (
          <p className="field-note mb-0">You’ve reached the five-location limit. Remove one to add another.</p>
        )}
      </form>

      {locations.length === 0 ? (
        <div className="empty-results">
          <i aria-hidden="true" className="bi bi-geo-alt" />
          <h3>No saved locations yet</h3>
          <p>Add a home, work, or other frequent job location above.</p>
        </div>
      ) : (
        <div className="saved-location-list">
          {locations.map((location) => (
            <article className="saved-location-card" key={location.id}>
              <span aria-hidden="true" className="saved-location-icon">
                <i className="bi bi-geo-alt" />
              </span>
              <div className="saved-location-copy">
                <h3>{location.name}</h3>
                <p>{location.address}</p>
              </div>
              <div className="saved-location-actions">
                <button
                  aria-label={`Edit ${location.name}`}
                  className="btn btn-sm btn-outline-dark"
                  disabled={Boolean(deletingId)}
                  onClick={() => startEdit(location)}
                  type="button"
                >
                  Edit
                </button>
                {deletingId === location.id ? (
                  <>
                    <button
                      className="btn btn-sm btn-danger"
                      disabled={Boolean(deletingId)}
                      onClick={() => deleteLocation(location)}
                      type="button"
                    >
                      Confirm remove
                    </button>
                    <button
                      className="btn btn-sm btn-link"
                      onClick={() => setDeletingId(null)}
                      type="button"
                    >
                      Keep
                    </button>
                  </>
                ) : (
                  <button
                    aria-label={`Remove ${location.name}`}
                    className="btn btn-sm btn-outline-danger"
                    disabled={Boolean(deletingId)}
                    onClick={() => setDeletingId(location.id)}
                    type="button"
                  >
                    Remove
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
