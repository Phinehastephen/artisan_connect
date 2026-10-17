import { Navigate, useLocation } from 'react-router-dom'
import { homeForRole, useAuth } from './AuthContext'

export default function RoleRoute({ allowedRoles, children }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <p aria-live="polite" className="auth-loading">Checking your session…</p>
  }
  if (!user) {
    return <Navigate replace state={{ from: location }} to="/login" />
  }
  if (!allowedRoles.includes(user.role)) {
    return <Navigate replace to={homeForRole(user.role)} />
  }
  return children
}