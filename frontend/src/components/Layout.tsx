import { CheckCircle2, FileClock, FileText, History, Home, LogOut, Search, Settings, UploadCloud, UserCog } from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function labels(language: string) {
  return language === 'en' ? {
    brandTop: 'Medical', brandBottom: 'Prescriptions', home: 'Home', upload: 'Upload Prescription', processing: 'Processing', validation: 'Validation', history: 'History', users: 'Users', settings: 'Settings', search: 'Search prescriptions or OCR text...', logout: 'Log out', admin: 'Administrator', pharmacist: 'Pharmaceutical chemist'
  } : {
    brandTop: 'Sistema de', brandBottom: 'Recetas Médicas', home: 'Inicio', upload: 'Subir Receta', processing: 'Procesamiento', validation: 'Validación', history: 'Historial', users: 'Usuarios', settings: 'Configuración', search: 'Buscar recetas o texto OCR...', logout: 'Cerrar sesión', admin: 'Administrador', pharmacist: 'Químico farmacéutico'
  }
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [language, setLanguage] = useState(localStorage.getItem('language') || 'es')
  useEffect(() => {
    const onStorage = () => setLanguage(localStorage.getItem('language') || 'es')
    window.addEventListener('storage', onStorage)
    const timer = window.setInterval(onStorage, 400)
    return () => { window.removeEventListener('storage', onStorage); window.clearInterval(timer) }
  }, [])
  const t = labels(language)
  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon"><FileText size={18} /></div>
          <div><strong>{t.brandTop}</strong><span>{t.brandBottom}</span></div>
        </div>
        <nav>
          <NavLink to="/"><Home size={17} /> {t.home}</NavLink>
          <NavLink to="/upload"><UploadCloud size={17} /> {t.upload}</NavLink>
          <NavLink to="/processing/0"><FileClock size={17} /> {t.processing}</NavLink>
          <NavLink to="/validation"><CheckCircle2 size={17} /> {t.validation}</NavLink>
          <NavLink to="/history"><History size={17} /> {t.history}</NavLink>
          {user?.role === 'admin' && <NavLink to="/users"><UserCog size={17} /> {t.users}</NavLink>}
          <NavLink to="/settings"><Settings size={17} /> {t.settings}</NavLink>
        </nav>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div className="search-box"><Search size={17} /><input placeholder={t.search} /></div>
          <div className="top-actions">
            <div className="avatar">{user?.photo_url ? <img src={user.photo_url} /> : user?.full_name?.charAt(0)}</div>
            <div className="user-label"><strong>{user?.full_name || 'Usuario'}</strong><span>{user?.role === 'admin' ? t.admin : t.pharmacist}</span></div>
            <button className="icon-button" onClick={handleLogout} title={t.logout}><LogOut size={18} /></button>
          </div>
        </header>
        <section className="page-content">{children}</section>
      </main>
    </div>
  )
}
