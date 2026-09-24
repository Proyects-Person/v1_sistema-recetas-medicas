import { Lock } from 'lucide-react'
import {
  FormEvent,
  useState
} from 'react'

import {
  Link,
  useNavigate
} from 'react-router-dom'

import {
  useAuth
} from '../context/AuthContext'


export default function Login() {

  const [
    email,
    setEmail
  ] = useState('')

  const [
    password,
    setPassword
  ] = useState('')

  const [
    remember,
    setRemember
  ] = useState(false)

  const [
    error,
    setError
  ] = useState('')

  const [
    loading,
    setLoading
  ] = useState(false)

  const {
    login
  } = useAuth()

  const navigate =
    useNavigate()


  const submit = async (
    event: FormEvent
  ) => {

    event.preventDefault()

    setError('')

    if (
      password.length < 6
    ) {

      setError(
        'La contraseña debe tener al menos 6 caracteres.'
      )

      return
    }

    setLoading(true)

    try {

      await login(
        email,
        password
      )

      navigate('/')

    } catch (err: any) {

      const message =
        err?.message ||
        'Credenciales incorrectas'

      setError(
        typeof message === 'string'
          ? message
          : 'Credenciales incorrectas'
      )

    } finally {

      setLoading(false)
    }
  }


  return (

    <div className="login-page">

      <section
        className="login-hero lab-hero"
      >

        <div
          className="lab-hero-overlay"
        >

          <h1>
            Sistema de Recetas Médicas
          </h1>

          <p>
            Farmacia magistral ·
            Validación farmacéutica ·
            Trazabilidad segura
          </p>

        </div>

      </section>


      <section
        className="login-card"
      >

        <div
          className="login-icon"
        >
          <Lock size={22} />
        </div>

        <h2>
          Bienvenido
        </h2>

        <p>
          Ingresa tus credenciales
          para continuar
        </p>


        <form
          onSubmit={submit}
        >

          <label>
            Correo electrónico
          </label>

          <input
            value={email}
            onChange={
              e =>
                setEmail(
                  e.target.value
                )
            }
            type="email"
            placeholder="correo@empresa.com"
            required
            autoComplete="username"
          />


          <label>
            Contraseña
          </label>

          <input
            value={password}
            onChange={
              e =>
                setPassword(
                  e.target.value
                )
            }
            type="password"
            placeholder="Contraseña"
            required
            autoComplete="current-password"
          />


          <div
            className="form-row"
          >

            <label
              className="check"
            >

              <input
                type="checkbox"
                checked={remember}
                onChange={
                  e =>
                    setRemember(
                      e.target.checked
                    )
                }
              />

              Recordarme

            </label>


            <Link
              className="forgot-link"
              to="/forgot-password"
            >
              ¿Olvidaste tu contraseña?
            </Link>

          </div>


          {
            error &&
            (
              <div
                className="error-box"
              >
                {error}
              </div>
            )
          }


          <button
            className="primary-btn"
            disabled={loading}
          >

            {
              loading
                ? 'Validando...'
                : 'Iniciar sesión'
            }

          </button>

        </form>

      </section>

    </div>
  )
}