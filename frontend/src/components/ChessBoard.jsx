import { Chessboard } from 'react-chessboard'

// Warm sage board that sits well in both themes.
const LIGHT_SQUARE = '#eaecd2'
const DARK_SQUARE = '#6b9150'

const BOARD_DEFAULTS = {
  allowDragging: false,
  boardStyle: {
    borderRadius: 10,
    overflow: 'hidden',
    boxShadow: '0 10px 30px rgb(0 0 0 / 0.35)',
  },
  lightSquareStyle: { backgroundColor: LIGHT_SQUARE },
  darkSquareStyle: { backgroundColor: DARK_SQUARE },
  lightSquareNotationStyle: { color: DARK_SQUARE, fontWeight: 700 },
  darkSquareNotationStyle: { color: LIGHT_SQUARE, fontWeight: 700 },
  animationDurationInMs: 180,
}

/** The app's chessboard: react-chessboard with the app's colors, rounded frame and animation. */
export default function ChessBoard({ options }) {
  return <Chessboard options={{ ...BOARD_DEFAULTS, ...options }} />
}
