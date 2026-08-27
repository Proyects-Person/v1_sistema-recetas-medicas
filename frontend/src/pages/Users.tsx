import { RefreshCw, Save, UserPlus } from 'lucide-react'
import { FormEvent, useEffect, useState } from 'react'
import { api } from '../services/api'
import type { User } from '../types'

function roleLabel(role: string) {
  return role === 'admin' ? 'Administrador' : 'Químico farmacéutico'
}

export default function Users() {
  const [users, setUsers] = useState<User[]>([])
  const [form, setForm] = useState({ full_name: '', dni: '', phone: '', email: '', password: '', role: 'quimico_farmaceutico' })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const load = () => api.get<User[]>('/users').then(setUsers).catch(err => setError(err.message))
  useEffect(() => { load() }, [])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setMessage(''); setError('')
    if (!/^\d{8}$/.test(form.dni)) { setError('El DNI debe contener exactamente 8 dígitos.'); return }
    if (!/^\d{9}$/.test(form.phone)) { setError('El teléfono debe contener exactamente 9 dígitos.'); return }
    setLoading(true)
    try {
      await api.post<User>('/users', form)
      setForm({ full_name: '', dni: '', phone: '', email: '', password: '', role: 'quimico_farmaceutico' })
      setMessage('Usuario creado correctamente.')
      await load()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const updateUser = async (user: User, patch: Partial<User>) => {
    setMessage(''); setError('')
    try {
      const updated = await api.put<User>(`/users/${user.id}`, patch)
      setUsers(items => items.map(item => item.id === updated.id ? updated : item))
      setMessage('Usuario actualizado correctamente.')
    } catch (err: any) {
      setError(err.message)
    }
  }

  return (
    <div className="page-stack">
      <div className="page-title-row"><div><h1>Usuarios</h1><p>Solo el administrador puede crear cuentas y asignar roles</p></div></div>
      {message && <div className="success-box">{message}</div>}
      {error && <div className="error-box">{error}</div>}
      <div className="two-cols users-grid">
        <section className="card">
          <h2>Crear usuario</h2>
          <form className="form-stack" onSubmit={submit}>
            <label>Nombre completo</label>
            <input required value={form.full_name} onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))} />
            <label>DNI</label>
            <input required minLength={8} maxLength={8} inputMode="numeric" value={form.dni} onChange={e => setForm(f => ({ ...f, dni: e.target.value.replace(/[^0-9]/g, '').slice(0, 8) }))} placeholder="8 dígitos" />
            <label>Teléfono de contacto</label>
            <input required minLength={9} maxLength={9} inputMode="numeric" value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value.replace(/[^0-9]/g, '').slice(0, 9) }))} placeholder="9 dígitos" />
            <label>Correo</label>
            <input required type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
            <label>Contraseña temporal</label>
            <input required type="password" minLength={6} value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
            <label>Rol</label>
            <select value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}>
              <option value="quimico_farmaceutico">Químico farmacéutico</option>
              <option value="admin">Administrador</option>
            </select>
            <button className="primary-btn" disabled={loading}><UserPlus size={16} /> {loading ? 'Creando...' : 'Crear cuenta'}</button>
          </form>
        </section>
        <section className="card users-list-card">
          <div className="page-title-row compact"><div><h2>Personal registrado</h2><p>Administración de accesos del sistema</p></div><button className="outline-btn" onClick={load}><RefreshCw size={15} /> Actualizar</button></div>
          <div className="table-wrap">
            <table className="users-table">
              <thead><tr><th>Nombre</th><th>DNI</th><th>Teléfono</th><th>Correo</th><th>Rol</th><th>Estado</th><th>Acciones</th></tr></thead>
              <tbody>
                {users.map(user => (
                  <tr key={user.id}>
                    <td>{user.full_name}</td>
                    <td>{user.dni || 'No registrado'}</td>
                    <td>{user.phone || 'No registrado'}</td>
                    <td>{user.email}</td>
                    <td>
                      <select value={user.role} onChange={e => updateUser(user, { role: e.target.value })}>
                        <option value="quimico_farmaceutico">Químico farmacéutico</option>
                        <option value="admin">Administrador</option>
                      </select>
                    </td>
                    <td>{user.is_active ? 'Activo' : 'Inactivo'}</td>
                    <td className="row-actions">
                      <button className="outline-btn" onClick={() => updateUser(user, { is_active: !user.is_active })}>
                        <Save size={14} /> {user.is_active ? 'Desactivar' : 'Activar'}
                      </button>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && <tr><td colSpan={7}>No hay usuarios registrados.</td></tr>}
              </tbody>
            </table>
          </div>
          <p className="muted-text">Roles disponibles: {roleLabel('admin')} y {roleLabel('quimico_farmaceutico')}.</p>
        </section>
      </div>
    </div>
  )
}
