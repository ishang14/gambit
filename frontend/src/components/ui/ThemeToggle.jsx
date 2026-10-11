import { useTheme } from '../../theme/useTheme.js'
import Icon from './Icon.jsx'

export default function ThemeToggle() {
  const { theme, toggle } = useTheme()
  const next = theme === 'dark' ? 'light' : 'dark'
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next} theme`}
      className="btn btn-ghost h-9 w-9 !p-0"
    >
      <Icon name={theme === 'dark' ? 'sun' : 'moon'} className="h-[18px] w-[18px]" />
    </button>
  )
}
