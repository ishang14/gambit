import { fireEvent, render, screen } from '@testing-library/react'
import UserMenu from './UserMenu.jsx'

const EMAIL = 'magnus@example.com'

function setup() {
  const onLogout = vi.fn()
  render(
    <>
      <UserMenu email={EMAIL} onLogout={onLogout} />
      <button type="button">Somewhere else</button>
    </>,
  )
  return { onLogout, trigger: screen.getByRole('button', { name: 'Account menu' }) }
}

it('shows only the initial until opened', () => {
  const { trigger } = setup()

  expect(trigger).toHaveTextContent('M')
  expect(trigger).toHaveAttribute('aria-expanded', 'false')
  expect(screen.queryByText(EMAIL)).not.toBeInTheDocument()
  expect(screen.queryByRole('menu')).not.toBeInTheDocument()
})

it('opens a menu with the email and a log out button, and toggles closed', () => {
  const { trigger } = setup()

  fireEvent.click(trigger)

  expect(trigger).toHaveAttribute('aria-expanded', 'true')
  expect(screen.getByRole('menu', { name: 'Account' })).toBeInTheDocument()
  expect(screen.getByText(EMAIL)).toBeInTheDocument()
  expect(screen.getByRole('menuitem', { name: 'Log out' })).toBeInTheDocument()

  fireEvent.click(trigger)
  expect(screen.queryByRole('menu')).not.toBeInTheDocument()
})

it('logs out and closes', () => {
  const { trigger, onLogout } = setup()
  fireEvent.click(trigger)

  fireEvent.click(screen.getByRole('menuitem', { name: 'Log out' }))

  expect(onLogout).toHaveBeenCalledTimes(1)
  expect(screen.queryByRole('menu')).not.toBeInTheDocument()
})

it('closes on Escape and returns focus to the avatar', () => {
  const { trigger } = setup()
  fireEvent.click(trigger)

  fireEvent.keyDown(document, { key: 'Escape' })

  expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  expect(trigger).toHaveFocus()
})

it('closes when you click elsewhere, but not when you click inside the menu', () => {
  const { trigger } = setup()
  fireEvent.click(trigger)

  fireEvent.pointerDown(screen.getByText(EMAIL))
  expect(screen.getByRole('menu')).toBeInTheDocument()

  fireEvent.pointerDown(screen.getByRole('button', { name: 'Somewhere else' }))
  expect(screen.queryByRole('menu')).not.toBeInTheDocument()
})

it('closes when focus moves out of the menu', () => {
  const { trigger } = setup()
  fireEvent.click(trigger)

  fireEvent.blur(trigger, { relatedTarget: screen.getByRole('button', { name: 'Somewhere else' }) })

  expect(screen.queryByRole('menu')).not.toBeInTheDocument()
})

it('stays open when focus moves from the avatar into the menu', () => {
  const { trigger } = setup()
  fireEvent.click(trigger)

  fireEvent.blur(trigger, { relatedTarget: screen.getByRole('menuitem', { name: 'Log out' }) })

  expect(screen.getByRole('menu')).toBeInTheDocument()
})
