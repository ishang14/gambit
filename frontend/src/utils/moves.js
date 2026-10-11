/** Move number prefix for the move at 0-based `plyIndex`: 0 -> "1.", 1 -> "1...", 2 -> "2." */
export function moveNumber(plyIndex) {
  const number = Math.floor(plyIndex / 2) + 1
  return plyIndex % 2 === 0 ? `${number}.` : `${number}...`
}

/** ["e4", "e5", "Nf3"] -> "1. e4 e5 2. Nf3" */
export function formatLine(sans) {
  return sans.map((san, index) => (index % 2 === 0 ? `${index / 2 + 1}. ${san}` : san)).join(' ')
}

/** Board-loadable FEN from a normalized one (no move counters). */
export function fenFromKey(fenKey) {
  return `${fenKey} 0 1`
}
