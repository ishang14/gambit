export const CLASSIFICATIONS = ['best', 'good', 'inaccuracy', 'mistake', 'blunder']

export const CLASSIFICATION_STYLES = {
  best: { label: 'Best', text: 'text-cls-best', dot: 'bg-cls-best', badge: 'bg-cls-best/15 text-cls-best', square: 'rgba(129, 182, 76, 0.55)' },
  good: { label: 'Good', text: 'text-cls-good', dot: 'bg-cls-good', badge: 'bg-cls-good/15 text-cls-good', square: 'rgba(14, 165, 233, 0.45)' },
  inaccuracy: { label: 'Inaccuracy', text: 'text-cls-inaccuracy', dot: 'bg-cls-inaccuracy', badge: 'bg-cls-inaccuracy/15 text-cls-inaccuracy', square: 'rgba(234, 179, 8, 0.55)' },
  mistake: { label: 'Mistake', text: 'text-cls-mistake', dot: 'bg-cls-mistake', badge: 'bg-cls-mistake/15 text-cls-mistake', square: 'rgba(234, 120, 12, 0.55)' },
  blunder: { label: 'Blunder', text: 'text-cls-blunder', dot: 'bg-cls-blunder', badge: 'bg-cls-blunder/15 text-cls-blunder', square: 'rgba(220, 38, 38, 0.55)' },
}

// Marks shown next to moves in the move list.
export const CLASSIFICATION_SYMBOLS = {
  inaccuracy: '?!',
  mistake: '?',
  blunder: '??',
}
