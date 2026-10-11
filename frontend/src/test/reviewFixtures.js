// Scholar's mate, matching backend/tests/fakes.py.
export const SCHOLARS_MATE_PGN = `[Event "Test"]
[White "hikaru"]
[Black "villain"]
[Result "1-0"]

1. e4 {[%clk 0:09:58]} 1... e5 {[%clk 0:09:57]} 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0`

export const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

export function makeGame(overrides = {}) {
  return {
    id: 'game1',
    source_url: 'https://www.chess.com/game/live/1',
    white: 'hikaru',
    black: 'villain',
    white_rating: 1500,
    black_rating: 1450,
    user_color: 'white',
    user_rating: 1500,
    opponent: 'villain',
    opponent_rating: 1450,
    result: '1-0',
    user_result: 'win',
    time_control: '600',
    time_class: 'rapid',
    rated: true,
    played_at: '2026-09-15T12:00:00Z',
    eco: 'C20',
    opening: "King's Pawn Opening",
    ply_count: 7,
    analysis_status: 'none',
    analysis_job_id: null,
    analysis_progress: null,
    accuracy: null,
    opponent_accuracy: null,
    pgn: SCHOLARS_MATE_PGN,
    ...overrides,
  }
}

const cp = (value) => ({ cp: value, mate: null })

function move(ply, san, uci, classification, before, after, best, bestSan, loss = 0) {
  return {
    ply,
    color: ply % 2 === 1 ? 'white' : 'black',
    fen: 'unused',
    move_played: uci,
    move_san: san,
    best_move: best,
    best_move_san: bestSan,
    eval_before: before,
    eval_after: after,
    win_chance_loss: loss,
    cp_loss: 0,
    accuracy: 100 - loss,
    classification,
  }
}

export const SCHOLARS_MATE_ANALYSIS = {
  game_id: 'game1',
  depth: 14,
  accuracy: { white: 96.4, black: 68.2 },
  counts: {
    white: { best: 3, good: 1, inaccuracy: 0, mistake: 0, blunder: 0 },
    black: { best: 2, good: 0, inaccuracy: 0, mistake: 0, blunder: 1 },
  },
  moves: [
    move(1, 'e4', 'e2e4', 'best', cp(30), cp(30), 'e2e4', 'e4'),
    move(2, 'e5', 'e7e5', 'best', cp(30), cp(30), 'e7e5', 'e5'),
    move(3, 'Qh5', 'd1h5', 'good', cp(30), cp(-20), 'g1f3', 'Nf3', 4.6),
    move(4, 'Nc6', 'b8c6', 'best', cp(-20), cp(-20), 'b8c6', 'Nc6'),
    move(5, 'Bc4', 'f1c4', 'best', cp(-20), cp(-10), 'f1c4', 'Bc4'),
    move(6, 'Nf6', 'g8f6', 'blunder', cp(-10), { cp: null, mate: 1 }, 'g7g6', 'g6', 50.9),
    move(7, 'Qxf7#', 'h5f7', 'best', { cp: null, mate: 1 }, { cp: null, mate: 0 }, 'h5f7', 'Qxf7#'),
  ],
}
