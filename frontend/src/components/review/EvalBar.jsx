import { formatEval, whiteWinPercent } from '../../utils/evaluation.js'

/** Vertical bar: White's share grows from the bottom (or the top when the board is flipped). */
export default function EvalBar({ evaluation, whiteToMove, orientation = 'white' }) {
  const white = evaluation ? whiteWinPercent(evaluation, whiteToMove) : 50
  const label = evaluation ? formatEval(evaluation, whiteToMove) : '–'
  const whiteAtBottom = orientation === 'white'
  const whiteAhead = white >= 50
  // The label sits at the end of the bigger side; pick the text color for the region it lands in.
  const labelAtBottom = whiteAhead === whiteAtBottom
  const labelInWhite = labelAtBottom === whiteAtBottom

  return (
    <div
      role="meter"
      aria-label="Evaluation"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(white)}
      aria-valuetext={label}
      className={`relative flex w-8 shrink-0 overflow-hidden rounded-lg bg-[#2b2824] shadow-inner ring-1 ring-black/20 ${
        whiteAtBottom ? 'flex-col-reverse' : 'flex-col'
      }`}
    >
      <div className="bg-[#f3f0ea] transition-all duration-500" style={{ height: `${white}%` }} />
      <span
        className={`absolute left-0 right-0 text-center text-[10px] font-bold ${labelAtBottom ? 'bottom-1.5' : 'top-1.5'} ${
          labelInWhite ? 'text-[#2b2824]' : 'text-[#f3f0ea]'
        }`}
      >
        {label}
      </span>
    </div>
  )
}
