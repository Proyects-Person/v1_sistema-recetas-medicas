import type { ReactElement } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { useAuth } from './context/AuthContext'
import Dashboard from './pages/Dashboard'
import History from './pages/History'
import Login from './pages/Login'
import Processing from './pages/Processing'
import Settings from './pages/Settings'
import UploadRecipe from './pages/UploadRecipe'
import Users from './pages/Users'
import Validation from './pages/Validation'

function Protected({ children }: { children: ReactElement }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="boot-screen">Cargando sistema...</div>
  if (!user) return <Navigate to="/login" replace />
  return <Layout>{children}</Layout>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Protected><Dashboard /></Protected>} />
      <Route path="/upload" element={<Protected><UploadRecipe /></Protected>} />
      <Route path="/processing/:id" element={<Protected><Processing /></Protected>} />
      <Route path="/validation/:id?" element={<Protected><Validation /></Protected>} />
      <Route path="/history" element={<Protected><History /></Protected>} />
      <Route path="/settings" element={<Protected><Settings /></Protected>} />
      <Route path="/users" element={<Protected><Users /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
