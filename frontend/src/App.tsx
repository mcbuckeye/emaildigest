import { Routes, Route, Navigate } from 'react-router-dom'
import Auth from './pages/Auth'
import Dashboard from './pages/Dashboard'
import DigestEditor from './pages/DigestEditor'
import Layout from './components/Layout'
import AiAssistant from './pages/AiAssistant'
import Deliveries, { DeliveryPreview } from './pages/Deliveries'
import { PasswordResetRequest, PasswordResetConfirm } from './pages/PasswordReset'
import VerifyEmail from './pages/VerifyEmail'
import Unsubscribe from './pages/Unsubscribe'
import Settings from './pages/Settings'
import { useAuth } from './contexts/AuthContext'

function RequireAuth({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="loader" aria-label="loading" />
  if (!user) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Auth mode="login" />} />
      <Route path="/signup" element={<Auth mode="signup" />} />
      <Route path="/forgot-password" element={<PasswordResetRequest />} />
      <Route path="/reset-password" element={<PasswordResetConfirm />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/unsubscribe" element={<Unsubscribe />} />
      <Route
        path="/*"
        element={
          <RequireAuth>
            <Layout>
              <Routes>
                <Route index element={<Dashboard />} />
                <Route path="digests/new" element={<DigestEditor />} />
                <Route path="digests/assistant" element={<AiAssistant />} />
                <Route path="digests/edit/:id" element={<DigestEditor />} />
                <Route path="digests/:id/deliveries" element={<Deliveries />} />
                <Route path="deliveries/:id/preview" element={<DeliveryPreview />} />
                <Route path="settings" element={<Settings />} />
              </Routes>
            </Layout>
          </RequireAuth>
        }
      />
    </Routes>
  )
}
