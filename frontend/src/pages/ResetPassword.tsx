import {
  ArrowLeft,
  LockKeyhole
} from 'lucide-react'

import {
  FormEvent,
  useState
} from 'react'

import {
  Link,
  useNavigate,
  useSearchParams
} from 'react-router-dom'

import {
  api
} from '../services/api'


export default function ResetPassword() {

  const [
    searchParams
  ] = useSearchParams()

  const token =
    searchParams.get('token') || ''

  const navigate =
    useNavigate()


  const [
    password,
    setPassword
  ] = useState('')

  const [
    confirmPassword,
    setConfirmPassword
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


    if (!token) {

      setError(
        'El enlace de recuperación no contiene un token válido.'
      )

      return
    }


    if (
      password.length < 6
    ) {

      setError(
        'La nueva contraseña debe tener al menos 6 caracteres.'
      )

      return
    }


    if (
      password !== confirmPassword
    ) {

      setError(
        'Las contraseñas no coinciden.'
      )

      return
    }


    setLoading(true)


    try {

      const response =
        await api.post<{
          message: string
        }>(
          '/auth/reset-password',
          {
            token,
            new_password: password
          }
        )


      setMessage(
        response.message
      )


      setPassword('')
      setConfirmPassword('')


      setTimeout(
        () => {

          navigate(
            '/login',
            {
              replace: true
            }
          )

        },
        1800
      )

    } catch (err: any) {

      setError(
        err?.message ||
        'No se pudo restablecer la contraseña.'
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

          <LockKeyhole
            size={22}
          />

        </div>


        <h2>
          Nueva contraseña
        </h2>

        <p>
          Crea una nueva contraseña
          para volver a ingresar al sistema.
        </p>


        <form
          onSubmit={submit}
        >

          <label>
            Nueva contraseña
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
            placeholder="Mínimo 6 caracteres"
            required
            autoComplete="new-password"
          />


          <label>
            Confirmar contraseña
          </label>

          <input
            value={confirmPassword}
            onChange={
              e =>
                setConfirmPassword(
                  e.target.value
                )
            }
            type="password"
            placeholder="Repite la nueva contraseña"
            required
            autoComplete="new-password"
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
            disabled={
              loading ||
              !token ||
              !!message
            }
          >

            {
              loading
                ? 'Actualizando...'
                : 'Restablecer contraseña'
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