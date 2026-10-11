import Icon from '../ui/Icon.jsx'

const BUTTONS = [
  { label: 'First move', icon: 'first', target: () => 0 },
  { label: 'Previous move', icon: 'prev', target: (ply) => ply - 1 },
  { label: 'Next move', icon: 'next', target: (ply) => ply + 1 },
  { label: 'Last move', icon: 'last', target: (ply, total) => total },
]

export default function BoardControls({ ply, total, onChange }) {
  return (
    <div className="flex justify-center gap-2">
      {BUTTONS.map(({ label, icon, target }) => {
        const next = target(ply, total)
        return (
          <button
            key={label}
            type="button"
            aria-label={label}
            title={label}
            disabled={next < 0 || next > total || next === ply}
            onClick={() => onChange(next)}
            className="btn btn-secondary h-10 w-14 !p-0"
          >
            <Icon name={icon} />
          </button>
        )
      })}
    </div>
  )
}
