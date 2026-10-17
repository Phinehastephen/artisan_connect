import { BrowserRouter, Link, NavLink, Route, Routes } from 'react-router-dom'
import { AuthProvider, homeForRole, useAuth } from './auth/AuthContext'
import RoleRoute from './auth/RoleRoute'
import LoginPage from './pages/LoginPage'
import PasswordResetPage from './pages/PasswordResetPage'
import RegisterPage from './pages/RegisterPage'
import './app-shell.css'

const workspaces = [
  {
    path: '/customer',
    title: 'Customer',
    description: 'Search for local artisans and manage bookings.',
    icon: 'bi-person',
  },
  {
    path: '/artisan',
    title: 'Artisan',
    description: 'Manage incoming jobs, services, and reviews.',
    icon: 'bi-tools',
  },
  {
    path: '/admin',
    title: 'Administration',
    description: 'Review accounts, service changes, and disputes.',
    icon: 'bi-shield-check',
  },
]

function WorkspacePicker() {
  return (
    <section aria-labelledby="workspace-title" className="workspace-page">
      <div className="page-heading">
        <p className="eyebrow">ARTISAN CONNECT</p>
        <h1 id="workspace-title">Choose a workspace</h1>
        <p className="page-intro">
          Sign-in and workspace permissions are added in the next phase.
        </p>
      </div>

      <div className="row g-3 workspace-grid">
        {workspaces.map((workspace) => (
          <div className="col-12 col-md-4" key={workspace.path}>
            <Link className="workspace-link" to={workspace.path}>
              <span aria-hidden="true" className="workspace-icon">
                <i className={`bi ${workspace.icon}`} />
              </span>
              <span className="workspace-copy">
                <span className="workspace-title">{workspace.title}</span>
                <span className="workspace-description">
                  {workspace.description}
                </span>
              </span>
              <i aria-hidden="true" className="bi bi-arrow-up-right workspace-arrow" />
            </Link>
          </div>
        ))}
      </div>

      <div className="foundation-note">
        <span className="foundation-dot" />
        <span>API base configured at <code>/api/v1</code></span>
      </div>
    </section>
  )
}

function WorkspacePlaceholder({ title }) {
  return (
    <section aria-labelledby="workspace-placeholder-title" className="workspace-page">
      <p className="eyebrow">WORKSPACE</p>
      <h1 id="workspace-placeholder-title">{title}</h1>
      <p className="page-intro">Your {title.toLowerCase()} screens will be built in the next phase.</p>
      <Link className="btn btn-outline-dark mt-3" to="/">
        <i aria-hidden="true" className="bi bi-arrow-left me-2" />
        All workspaces
      </Link>
    </section>
  )
}

function AppLayout() {
  const { user, loading, logout } = useAuth()

  return (
    <div className="app-frame">
      <header className="topbar">
        <Link aria-label="Artisan Connect home" className="brand" to="/">
          <span aria-hidden="true" className="brand-mark">A</span>
          <span>Artisan <strong>Connect</strong></span>
        </Link>
        <nav aria-label="Main navigation" className="topbar-nav">
          <NavLink
            className={({ isActive }) => `topbar-link${isActive ? ' active' : ''}`}
            end
            to="/"
          >
            Workspaces
          </NavLink>
          {user && (
            <NavLink
              className={({ isActive }) => `topbar-link${isActive ? ' active' : ''}`}
              to={homeForRole(user.role)}
            >
              {user.role === 'ADMIN' ? 'Administration' : `${user.role[0]}${user.role.slice(1).toLowerCase()} workspace`}
            </NavLink>
          )}
        </nav>
        {loading ? (
          <span aria-label="Loading session" className="session-indicator" role="status" />
        ) : user ? (
          <button className="btn btn-sm btn-outline-dark sign-in-link" onClick={() => void logout()} type="button">
            Sign out
          </button>
        ) : (
          <Link className="btn btn-sm btn-dark sign-in-link" to="/login">
            Sign in <i aria-hidden="true" className="bi bi-arrow-right ms-2" />
          </Link>
        )}
      </header>

      <main id="main-content">
        <Routes>
          <Route element={<WorkspacePicker />} path="/" />
          <Route element={<LoginPage />} path="/login" />
          <Route element={<RegisterPage />} path="/register" />
          <Route element={<PasswordResetPage />} path="/password-reset" />
          <Route
            element={(
              <RoleRoute allowedRoles={['CUSTOMER']}>
                <WorkspacePlaceholder title="Customer workspace" />
              </RoleRoute>
            )}
            path="/customer/*"
          />
          <Route
            element={(
              <RoleRoute allowedRoles={['ARTISAN']}>
                <WorkspacePlaceholder title="Artisan workspace" />
              </RoleRoute>
            )}
            path="/artisan/*"
          />
          <Route
            element={(
              <RoleRoute allowedRoles={['ADMIN']}>
                <WorkspacePlaceholder title="Administration" />
              </RoleRoute>
            )}
            path="/admin/*"
          />
          <Route element={<WorkspacePlaceholder title="Page not found" />} path="*" />
        </Routes>
      </main>

      <footer className="app-footer">
        <span>Artisan Connect</span>
        <span>Marketplace workspace</span>
      </footer>
    </div>
  )
}

export default function Application() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppLayout />
      </AuthProvider>
    </BrowserRouter>
  )
}