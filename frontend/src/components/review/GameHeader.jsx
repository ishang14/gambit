import { capitalize, formatDate, formatTimeControl } from '../../utils/format.js'
import Icon from '../ui/Icon.jsx'
import PageHeader from '../ui/PageHeader.jsx'

const RESULT_STYLES = {
  win: 'bg-brand/15 text-brand',
  loss: 'bg-danger/15 text-danger',
  draw: 'bg-raised text-ink-2',
}

function Player({ name, rating }) {
  return (
    <span className="font-semibold text-ink">
      {name}
      {rating && <span className="ml-1 font-normal text-muted">({rating})</span>}
    </span>
  )
}

export default function GameHeader({ game }) {
  return (
    <PageHeader title="Game Review">
      <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-ink-2">
        <Player name={game.white} rating={game.white_rating} />
        <span className="text-muted">vs</span>
        <Player name={game.black} rating={game.black_rating} />
        <span className={`badge ml-1 ${RESULT_STYLES[game.user_result]}`}>
          {game.result} · you {game.user_result === 'draw' ? 'drew' : game.user_result === 'win' ? 'won' : 'lost'}
        </span>
      </p>
      <p className="flex flex-wrap items-center gap-x-2 text-sm text-muted">
        <span>{formatDate(game.played_at)}</span>
        <span aria-hidden="true">·</span>
        <span>
          {capitalize(game.time_class)} {formatTimeControl(game.time_control)}
        </span>
        {game.opening && (
          <>
            <span aria-hidden="true">·</span>
            <span>{game.opening}</span>
          </>
        )}
        <span aria-hidden="true">·</span>
        <a
          href={game.source_url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-brand hover:underline"
        >
          Original game
          <Icon name="external" className="h-3.5 w-3.5" />
        </a>
      </p>
    </PageHeader>
  )
}
