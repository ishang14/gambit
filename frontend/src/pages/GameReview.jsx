import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchGameAnalysis } from '../api/analysis.js'
import { fetchGame } from '../api/games.js'
import ChessBoard from '../components/ChessBoard.jsx'
import AnalysisPanel from '../components/review/AnalysisPanel.jsx'
import BoardControls from '../components/review/BoardControls.jsx'
import EvalBar from '../components/review/EvalBar.jsx'
import GameHeader from '../components/review/GameHeader.jsx'
import MoveComment from '../components/review/MoveComment.jsx'
import MoveList from '../components/review/MoveList.jsx'
import PlayerBar from '../components/review/PlayerBar.jsx'
import Icon from '../components/ui/Icon.jsx'
import Spinner from '../components/ui/Spinner.jsx'
import { useAnalysisJob } from '../hooks/useAnalysisJob.js'
import { useGameMoves } from '../hooks/useGameMoves.js'
import { useMoveNavigation } from '../hooks/useMoveNavigation.js'
import { CLASSIFICATION_STYLES } from '../utils/classification.js'
import { isWhiteToMove } from '../utils/evaluation.js'

const LAST_MOVE_COLOR = 'rgba(250, 204, 21, 0.45)'
const BEST_MOVE_ARROW = 'rgba(22, 163, 74, 0.75)'

/** Engine evaluation of the position after `ply` moves. */
function evaluationAt(analysis, ply) {
  if (!analysis || analysis.moves.length === 0) return null
  return ply === 0 ? analysis.moves[0].eval_before : analysis.moves[ply - 1]?.eval_after ?? null
}

export default function GameReview() {
  const { gameId } = useParams()
  const [game, setGame] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [loadError, setLoadError] = useState(null)

  const load = useCallback(async () => {
    try {
      const loaded = await fetchGame(gameId)
      setGame(loaded)
      setAnalysis(loaded.analysis_status === 'done' ? await fetchGameAnalysis(gameId) : null)
    } catch (err) {
      setLoadError(err.message)
    }
  }, [gameId])

  useEffect(() => {
    load()
  }, [load])

  const parsed = useGameMoves(game?.pgn)
  const analysisJob = useAnalysisJob(game, load)
  const { ply, goTo } = useMoveNavigation(parsed?.moves.length ?? 0)

  if (loadError) {
    return (
      <p role="alert" className="alert alert-danger">
        {loadError}
      </p>
    )
  }
  if (!game) return <Spinner>Loading game…</Spinner>
  if (!parsed) return <p className="text-danger">Could not read this game&apos;s moves.</p>

  const topColor = game.user_color === 'white' ? 'black' : 'white'
  const fen = parsed.fens[ply]
  const lastMove = ply > 0 ? parsed.moves[ply - 1] : null
  const analyzedMove = ply > 0 ? analysis?.moves[ply - 1] : null
  const bestNext = analysis?.moves[ply]?.best_move

  const squareColor = analyzedMove ? CLASSIFICATION_STYLES[analyzedMove.classification].square : LAST_MOVE_COLOR
  const squareStyles = lastMove
    ? { [lastMove.from]: { backgroundColor: squareColor }, [lastMove.to]: { backgroundColor: squareColor } }
    : {}
  const arrows = bestNext
    ? [{ startSquare: bestNext.slice(0, 2), endSquare: bestNext.slice(2, 4), color: BEST_MOVE_ARROW }]
    : []

  return (
    <div className="space-y-6">
      <Link to="/games" className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-2 hover:text-brand">
        <Icon name="arrowLeft" className="h-4 w-4" />
        All games
      </Link>
      <GameHeader game={game} />

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,600px)_1fr]">
        <div className="card space-y-3 p-4">
          <PlayerBar game={game} color={topColor} analysis={analysis} />
          <div className="flex items-stretch gap-2.5">
            {analysis && (
              <EvalBar
                evaluation={evaluationAt(analysis, ply)}
                whiteToMove={isWhiteToMove(fen)}
                orientation={game.user_color}
              />
            )}
            <div className="min-w-0 flex-1">
              <ChessBoard
                options={{
                  id: 'review-board',
                  position: fen,
                  boardOrientation: game.user_color,
                  arrows,
                  squareStyles,
                }}
              />
            </div>
          </div>
          <PlayerBar game={game} color={game.user_color} analysis={analysis} />
          <BoardControls ply={ply} total={parsed.moves.length} onChange={goTo} />
          {analysis && <MoveComment move={analyzedMove} ply={ply} />}
        </div>

        <div className="space-y-4">
          <AnalysisPanel
            game={game}
            analysis={analysis}
            job={analysisJob.job}
            error={analysisJob.error}
            onAnalyze={analysisJob.start}
          />
          <MoveList
            moves={parsed.moves}
            classifications={analysis?.moves.map((m) => m.classification)}
            ply={ply}
            onSelect={goTo}
          />
        </div>
      </div>
    </div>
  )
}
