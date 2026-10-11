import { useState } from 'react'

/** Form state for the login/signup pages: field values, error message, submitting flag. */
export function useAuthForm(initialValues, submit) {
  const [values, setValues] = useState(initialValues)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  function handleChange(event) {
    setValues((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await submit(values)
    } catch (err) {
      setError(err.message)
      setSubmitting(false)
    }
  }

  return { values, error, submitting, handleChange, handleSubmit }
}
