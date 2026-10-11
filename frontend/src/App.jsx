import { lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import Login from './pages/Login.jsx'
import Signup from './pages/Signup.jsx'
import ImportGames from './pages/ImportGames.jsx'
import GameList from './pages/GameList.jsx'

// Pages with the chessboard or charts load on demand, keeping those libraries
// out of the bundle everyone downloads first.
const GameReview = lazy(() => import('./pages/GameReview.jsx'))
const OpeningTree = lazy(() => import('./pages/OpeningTree.jsx'))
const Training = lazy(() => import('./pages/Training.jsx'))
const Insights = lazy(() => import('./pages/Insights.jsx'))

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/games" replace />} />
          <Route path="/import" element={<ImportGames />} />
          <Route path="/games" element={<GameList />} />
          <Route path="/games/:gameId" element={<GameReview />} />
          <Route path="/openings" element={<OpeningTree />} />
          <Route path="/training" element={<Training />} />
          <Route path="/insights" element={<Insights />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
