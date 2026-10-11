// Mirrors backend/app/analysis/scoring.py. Evaluations are { cp, mate } from White's
// point of view; mate === 0 means the side to move has been checkmated.

const MATE_CP = 10000

export function whiteWinPercent(evaluation, whiteToMove) {
  const { cp, mate } = evaluation
  if (mate !== null && mate !== undefined) {
    if (mate === 0) return whiteToMove ? 0 : 100
    return mate > 0 ? 100 : 0
  }
  const clamped = Math.max(-MATE_CP, Math.min(MATE_CP, cp ?? 0))
  return 50 + 50 * (2 / (1 + Math.exp(-0.00368208 * clamped)) - 1)
}

/** "+1.3", "-0.4", "M3" (White mates), "-M2" (Black mates), "1-0" / "0-1" when mated. */
export function formatEval(evaluation, whiteToMove) {
  const { cp, mate } = evaluation
  if (mate !== null && mate !== undefined) {
    if (mate === 0) return whiteToMove ? '0-1' : '1-0'
    return mate > 0 ? `M${mate}` : `-M${-mate}`
  }
  const pawns = (cp ?? 0) / 100
  return `${pawns > 0 ? '+' : ''}${pawns.toFixed(1)}`
}

/** Side to move from a FEN string. */
export function isWhiteToMove(fen) {
  return fen.split(' ')[1] === 'w'
}
