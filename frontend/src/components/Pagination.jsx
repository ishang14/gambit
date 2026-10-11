export default function Pagination({ page, pageSize, total, onPageChange }) {
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1
  const last = Math.min(page * pageSize, total)
  const button = 'btn btn-secondary btn-sm'

  return (
    <nav aria-label="Pagination" className="flex items-center justify-between border-t border-line px-4 py-3 text-sm text-ink-2">
      <span>
        {first}–{last} of {total}
      </span>
      <div className="flex gap-2">
        <button type="button" className={button} disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          Previous
        </button>
        <button type="button" className={button} disabled={last >= total} onClick={() => onPageChange(page + 1)}>
          Next
        </button>
      </div>
    </nav>
  )
}
