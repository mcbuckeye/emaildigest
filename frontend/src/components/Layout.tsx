import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f3f4f6' }}>
      <nav className="nav">
        <div className="nav-content">
          <Link to="/" className="nav-logo">
            EmailDigest
          </Link>
          <div className="nav-links">
            <Link to="/">Dashboard</Link>
            <Link to="/digests/assistant">AI Assistant</Link>
            <Link to="/settings">Settings</Link>
            <span style={{ marginLeft: '24px', color: '#6b7280' }}>
              {user?.email}
            </span>
            <button className="btn btn-secondary btn-sm" onClick={handleLogout}>
              Logout
            </button>
          </div>
        </div>
      </nav>
      <main className="container">
        {children}
      </main>
    </div>
  )
}
