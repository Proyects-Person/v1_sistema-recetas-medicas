import {
  ArrowLeft,
  Mail
} from 'lucide-react'

import {
  FormEvent,
  useState
} from 'react'

import {
  Link
} from 'react-router-dom'

import {
  api
} from '../services/api'


export default function ForgotPassword() {

  const [
    email,
    setEmail
  ] = useState('')

  const [
    error,
    setError
  ] = useState('')

  const [
    message,
    setMessage
  ] = useState('')

  const [
    loading,
    setLoading
  ] = useState(false)


  const submit = async (
    event: FormEvent
  ) => {

    event.preventDefault()

    setError('')
    setMessage('')

    if (!email.trim()) {

      setError(
        'Ingresa tu correo electrónico.'
      )

      return
    }

    setLoading(true)

    try {

      const response =
        await api.post<{
          message: string
        }>(
          '/auth/forgot-password',
          {
            email: email.trim()
          }
        )

      setMessage(
        response.message
      )

    } catch (err: any) {

      setError(
        err?.message ||
        'No se pudo solicitar la recuperación de contraseña.'
      )

    } finally {

      setLoading(false)
    }
  }


  return (

    <div
      className="login-page"
    >

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
          <Mail size={22} />
        </div>

        <h2>
          Recuperar contraseña
        </h2>

        <p>
          Ingresa el correo asociado
          a tu cuenta.
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
            autoComplete="email"
          />


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


          {
            message &&
            (
              <div
                className="success-box"
              >
                {message}
              </div>
            )
          }


          <button
            className="primary-btn"
            disabled={loading}
          >

            {
              loading
                ? 'Enviando...'
                : 'Enviar enlace de recuperación'
            }

          </button>


          <div
            className="auth-back-link"
          >

            <Link
              to="/login"
            >

              <ArrowLeft
                size={16}
              />

              Volver al inicio de sesión

            </Link>

          </div>

        </form>

      </section>

    </div>
  )
}