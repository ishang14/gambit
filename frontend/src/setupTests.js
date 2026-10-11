import '@testing-library/jest-dom/vitest'
import { configure } from '@testing-library/react'

// The full suite runs files in parallel; under that load some renders take just over
// Testing Library's 1s default.
configure({ asyncUtilTimeout: 3000 })

// Tests must never reach a real server. mockApi() stubs fetch per test; a request made
// outside a stub (e.g. a page effect that fires after its test finished) gets this
// instead of hitting whatever is running on localhost.
globalThis.fetch = (url) => Promise.reject(new Error(`Unexpected real fetch in a test: ${url}`))
