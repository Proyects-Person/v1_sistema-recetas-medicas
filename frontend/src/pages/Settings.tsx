import { Save, Upload } from 'lucide-react'
import { ChangeEvent, FormEvent, useEffect, useState } from 'react'
import { applyUserConfig, useAuth } from '../context/AuthContext'
import { api } from '../services/api'
import type { User, UserConfig } from '../types'

export default function Settings() {
  const { user, refreshUser } = useAuth()

  const [profile, setProfile] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
    dni: user?.dni || '',
    phone: user?.phone || ''
  })

  const [config, setConfig] = useState({
    notifications: true,
    theme: 'claro',
    language: 'es'
  })

  const [password, setPassword] = useState({
    current_password: '',
    new_password: ''
  })

  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [changingPassword, setChangingPassword] = useState(false)

  useEffect(() => {
    api.get<UserConfig>('/config')
      .then(c => {
        const next = {
          notifications: c.notifications,
          theme: c.theme,
          language: c.language
        }

        setConfig(next)
        applyUserConfig(next)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (user) {
      setProfile({
        full_name: user.full_name || '',
        email: user.email || '',
        dni: user.dni || '',
        phone: user.phone || ''
      })
    }
  }, [user?.id])

  const saveProfile = async (event: FormEvent) => {
    event.preventDefault()
    setMessage('')
    setError('')

    if (profile.dni && !/^\d{8}$/.test(profile.dni)) {
      setError('El DNI debe contener exactamente 8 dígitos.')
      return
    }

    if (profile.phone && !/^\d{9}$/.test(profile.phone)) {
      setError('El teléfono debe contener exactamente 9 dígitos.')
      return
    }

    try {
      await api.put<User>('/users/me', profile)
      await refreshUser()
      setMessage('Perfil actualizado correctamente.')
    } catch (err: any) {
      setError(err.message)
    }
  }

  const saveConfig = async () => {
    setMessage('')
    setError('')

    try {
      const saved = await api.put<UserConfig>('/config', config)
      applyUserConfig(saved)

      setMessage(
        config.language === 'en'
          ? 'Settings saved successfully.'
          : 'Configuración guardada correctamente.'
      )
    } catch (err: any) {
      setError(err.message)
    }
  }

  const changePassword = async () => {
    if (changingPassword) {
      return
    }

    setMessage('')
    setError('')

    const english = config.language === 'en'

    if (!password.current_password) {
      setError(
        english
          ? 'Enter your current password.'
          : 'Ingresa tu contraseña actual.'
      )
      return
    }

    if (!password.new_password) {
      setError(
        english
          ? 'Enter the new password.'
          : 'Ingresa la nueva contraseña.'
      )
      return
    }

    // Contar caracteres sin modificar la contraseña ingresada.
    const passwordLength = Array.from(password.new_password).length

    if (passwordLength < 6) {
      setError(
        english
          ? 'The new password must contain at least 6 characters.'
          : 'La nueva contraseña debe contener al menos 6 caracteres.'
      )
      return
    }

    if (passwordLength > 128) {
      setError(
        english
          ? 'The new password must not exceed 128 characters.'
          : 'La nueva contraseña no debe superar los 128 caracteres.'
      )
      return
    }

    setChangingPassword(true)

    try {
      await api.post('/auth/change-password', password)

      setPassword({
        current_password: '',
        new_password: ''
      })

      setMessage(
        english
          ? 'Password updated successfully.'
          : 'Contraseña actualizada correctamente.'
      )
    } catch (err: unknown) {
      // api.ts ya extrae el detalle del backend y lo guarda en message.
      if (err instanceof Error && err.message) {
        setError(err.message)
      } else {
        setError(
          english
            ? 'Could not change the password. Please try again.'
            : 'No se pudo cambiar la contraseña. Inténtalo nuevamente.'
        )
      }
    } finally {
      setChangingPassword(false)
    }
  }

  const uploadPhoto = async (
    event: ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0]

    if (!file) {
      return
    }

    const form = new FormData()
    form.append('file', file)

    try {
      await api.upload<User>('/users/me/photo', form)
      await refreshUser()

      setMessage(
        config.language === 'en'
          ? 'Photo updated successfully.'
          : 'Foto actualizada correctamente.'
      )
    } catch (err: any) {
      setError(err.message)
    }
  }

  const t = config.language === 'en'
    ? {
        title: 'Settings',
        subtitle: 'Profile, security and system preferences',
        profile: 'Personal data',
        fullName: 'Full name',
        email: 'Email',
        dni: 'DNI',
        phone: 'Phone',
        saveProfile: 'Save profile',
        upload: 'Upload profile photo',
        security: 'Security',
        current: 'Current password',
        next: 'New password',
        change: 'Change password',
        changing: 'Changing password...',
        pref: 'Preferences',
        notif: 'Notifications enabled',
        theme: 'Theme',
        light: 'Light',
        dark: 'Dark',
        lang: 'Language',
        spanish: 'Spanish',
        english: 'English',
        save: 'Save settings'
      }
    : {
        title: 'Configuración',
        subtitle: 'Gestión de perfil, seguridad y preferencias del sistema',
        profile: 'Datos personales',
        fullName: 'Nombre completo',
        email: 'Correo electrónico',
        dni: 'DNI',
        phone: 'Teléfono',
        saveProfile: 'Guardar perfil',
        upload: 'Subir foto de perfil',
        security: 'Seguridad',
        current: 'Contraseña actual',
        next: 'Nueva contraseña',
        change: 'Cambiar contraseña',
        changing: 'Cambiando contraseña...',
        pref: 'Preferencias',
        notif: 'Notificaciones activas',
        theme: 'Tema',
        light: 'Claro',
        dark: 'Oscuro',
        lang: 'Idioma',
        spanish: 'Español',
        english: 'Inglés',
        save: 'Guardar configuración'
      }

  return (
    <div className="page-stack">
      <div className="page-title-row">
        <div>
          <h1>{t.title}</h1>
          <p>{t.subtitle}</p>
        </div>
      </div>

      {message && (
        <div className="success-box" role="status">
          {message}
        </div>
      )}

      {error && (
        <div className="error-box" role="alert">
          {error}
        </div>
      )}

      <div className="two-cols">
        <section className="card">
          <h2>{t.profile}</h2>

          <form className="form-stack" onSubmit={saveProfile}>
            <label>{t.fullName}</label>
            <input
              value={profile.full_name}
              onChange={e =>
                setProfile(p => ({
                  ...p,
                  full_name: e.target.value
                }))
              }
            />

            <label>{t.email}</label>
            <input
              type="email"
              value={profile.email}
              onChange={e =>
                setProfile(p => ({
                  ...p,
                  email: e.target.value
                }))
              }
            />

            <label>{t.dni}</label>
            <input
              inputMode="numeric"
              maxLength={8}
              value={profile.dni}
              onChange={e =>
                setProfile(p => ({
                  ...p,
                  dni: e.target.value
                    .replace(/[^0-9]/g, '')
                    .slice(0, 8)
                }))
              }
            />

            <label>{t.phone}</label>
            <input
              inputMode="numeric"
              maxLength={9}
              value={profile.phone}
              onChange={e =>
                setProfile(p => ({
                  ...p,
                  phone: e.target.value
                    .replace(/[^0-9]/g, '')
                    .slice(0, 9)
                }))
              }
            />

            <button className="primary-btn">
              <Save size={16} />
              {t.saveProfile}
            </button>
          </form>

          <label className="upload-photo">
            <Upload size={16} />
            {t.upload}
            <input
              type="file"
              hidden
              accept="image/*"
              onChange={uploadPhoto}
            />
          </label>
        </section>

        <section className="card">
          <h2>{t.security}</h2>

          <div className="form-stack">
            <label htmlFor="current-password">
              {t.current}
            </label>
            <input
              id="current-password"
              type="password"
              autoComplete="current-password"
              value={password.current_password}
              disabled={changingPassword}
              onChange={e =>
                setPassword(p => ({
                  ...p,
                  current_password: e.target.value
                }))
              }
            />

            <label htmlFor="new-password">
              {t.next}
            </label>
            <input
              id="new-password"
              type="password"
              autoComplete="new-password"
              value={password.new_password}
              disabled={changingPassword}
              onChange={e =>
                setPassword(p => ({
                  ...p,
                  new_password: e.target.value
                }))
              }
            />

            <button
              type="button"
              className="outline-btn"
              onClick={changePassword}
              disabled={changingPassword}
            >
              {changingPassword ? t.changing : t.change}
            </button>
          </div>
        </section>
      </div>

      <section className="card">
        <h2>{t.pref}</h2>

        <div className="settings-grid">
          <label className="switch-row">
            <input
              type="checkbox"
              checked={config.notifications}
              onChange={e =>
                setConfig(c => ({
                  ...c,
                  notifications: e.target.checked
                }))
              }
            />
            {t.notif}
          </label>

          <label>
            {t.theme}
            <select
              value={config.theme}
              onChange={e => {
                const next = {
                  ...config,
                  theme: e.target.value
                }
                setConfig(next)
                applyUserConfig(next)
              }}
            >
              <option value="claro">{t.light}</option>
              <option value="oscuro">{t.dark}</option>
            </select>
          </label>

          <label>
            {t.lang}
            <select
              value={config.language}
              onChange={e => {
                const next = {
                  ...config,
                  language: e.target.value
                }
                setConfig(next)
                applyUserConfig(next)
              }}
            >
              <option value="es">{t.spanish}</option>
              <option value="en">{t.english}</option>
            </select>
          </label>

          <button
            className="primary-link"
            onClick={saveConfig}
          >
            <Save size={16} />
            {t.save}
          </button>
        </div>
      </section>
    </div>
  )
}