/**
 * App.jsx — Root component.
 *
 * Handles routing between the HomePage (search + results) and the
 * ReviewPage (saved review history). Also owns the dark/light mode toggle
 * state so it can be passed down via props.
 */
import React, { useState, useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import ReviewPage from './pages/ReviewPage'
import { Moon, Sun, FlaskConical } from 'lucide-react'

export default function App() {
  /** dark — whether dark mode is active */
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem('theme')
    if (saved) return saved === 'dark'
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })

  // Sync the <html> class and localStorage whenever dark changes
  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }, [dark])

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100 transition-colors duration-200">
      {/* Top navigation bar */}
      <nav className="sticky top-0 z-10 border-b border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          {/* Brand */}
          <a href="/" className="flex items-center gap-2 font-semibold text-accent-600 dark:text-accent-400 hover:opacity-80 transition-opacity">
            <FlaskConical size={20} />
            <span>ResearchPipeline</span>
          </a>

          {/* Navigation links + theme toggle */}
          <div className="flex items-center gap-4">
            <a href="/" className="text-sm text-slate-600 dark:text-slate-400 hover:text-accent-600 dark:hover:text-accent-400 transition-colors">
              Search
            </a>
            <a href="/reviews" className="text-sm text-slate-600 dark:text-slate-400 hover:text-accent-600 dark:hover:text-accent-400 transition-colors">
              Saved Reviews
            </a>

            {/* Dark / light mode toggle button */}
            <button
              onClick={() => setDark(d => !d)}
              aria-label="Toggle dark mode"
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all"
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </div>
      </nav>

      {/* Page content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/reviews" element={<ReviewPage />} />
          <Route path="/reviews/:filename" element={<ReviewPage />} />
        </Routes>
      </main>
    </div>
  )
}
