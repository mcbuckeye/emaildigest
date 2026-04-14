import React from 'react'
// satisfy TS import usage check
void React
import { Routes, Route, Navigate } from 'react-router-dom'
import Auth from './pages/Auth'
import Dashboard from './pages/Dashboard'
import DigestEditor from './pages/DigestEditor'
import Layout from './components/Layout'
import { useAuth } from './contexts/AuthContext'

function App() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <div className="loader"></div>
      </div>
    )
  }

  return (
    <Routes>
      {/* Auth routes - no layout */}
      <Route path="/login" element={<Auth mode="login" />} />
      <Route path="/signup" element={<Auth mode="signup" />} />
      
      {/* Protected routes - wrapped in layout */}
      <Route
        path="/"
        element={
          user ? (
            <Layout>
              <Routes>
                <Route index element={<Dashboard />} />
                <Route path="digests/new" element={<DigestEditor />} />
                <Route path="digests/edit/:id" element={<DigestEditor />} />
                <Route path="digests/:id" element={<Dashboard />} />
              </Routes>
            </Layout>
          ) : (
            <Navigate to="/login" />
          )
        }
      />
    </Routes>
  )
}

export default App
