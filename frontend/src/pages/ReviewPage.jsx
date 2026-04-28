/**
 * ReviewPage.jsx — Saved reviews browser.
 *
 * Layout:
 *   Left sidebar — list of saved review summaries from GET /api/research/history
 *   Main panel  — selected review rendered via LiteratureReview
 *
 * Route params:
 *   /reviews           — list only
 *   /reviews/:filename — list + pre-selected review
 */
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getHistory, getReview } from '../api/researchApi'
import LiteratureReview from '../components/LiteratureReview'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorBanner from '../components/ErrorBanner'
import { BookOpen, Clock, ChevronRight } from 'lucide-react'

export default function ReviewPage() {
  const { filename } = useParams()
  const navigate = useNavigate()

  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [historyError, setHistoryError] = useState(null)

  const [selectedReview, setSelectedReview] = useState(null)
  const [reviewLoading, setReviewLoading] = useState(false)
  const [reviewError, setReviewError] = useState(null)

  // Load review history on mount
  useEffect(() => {
    let cancelled = false

    async function load() {
      setHistoryLoading(true)
      setHistoryError(null)
      try {
        const data = await getHistory()
        if (!cancelled) setHistory(data.reviews || [])
      } catch (err) {
        if (!cancelled) setHistoryError(err.message)
      } finally {
        if (!cancelled) setHistoryLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [])

  // Load a specific review when filename route param changes
  useEffect(() => {
    if (!filename) {
      setSelectedReview(null)
      return
    }

    let cancelled = false

    async function load() {
      setReviewLoading(true)
      setReviewError(null)
      try {
        const data = await getReview(filename)
        if (!cancelled) setSelectedReview(data)
      } catch (err) {
        if (!cancelled) setReviewError(err.message)
      } finally {
        if (!cancelled) setReviewLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [filename])

  function handleSelectReview(rev) {
    navigate(`/reviews/${encodeURIComponent(rev.filename)}`)
  }

  /** Format an ISO timestamp into a readable date string */
  function formatDate(iso) {
    if (!iso) return ''
    try {
      return new Date(iso).toLocaleDateString(undefined, {
        year: 'numeric', month: 'short', day: 'numeric',
      })
    } catch {
      return iso
    }
  }

  return (
    <div className="flex gap-6 min-h-[60vh]">
      {/* ── Sidebar: review history list ── */}
      <aside className="w-full sm:w-64 flex-shrink-0 space-y-3">
        <h2 className="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2">
          <BookOpen size={18} /> Saved Reviews
        </h2>

        {historyLoading && <LoadingSpinner message="Loading history…" size="sm" />}
        {historyError && <ErrorBanner message={historyError} />}

        {!historyLoading && !historyError && history.length === 0 && (
          <p className="text-sm text-slate-400 dark:text-slate-500">
            No saved reviews yet. Run the pipeline to generate one.
          </p>
        )}

        <ul className="space-y-1.5">
          {history.map(rev => (
            <li key={rev.filename}>
              <button
                onClick={() => handleSelectReview(rev)}
                className={`w-full text-left px-3 py-2.5 rounded-lg border transition-colors text-sm ${
                  filename === rev.filename
                    ? 'border-accent-400 bg-accent-50 dark:bg-accent-900/20 text-accent-700 dark:text-accent-400'
                    : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-accent-300 dark:hover:border-accent-600 text-slate-700 dark:text-slate-300'
                }`}
              >
                <div className="flex items-start justify-between gap-1">
                  <span className="font-medium line-clamp-2 leading-snug">{rev.topic}</span>
                  <ChevronRight size={14} className="flex-shrink-0 mt-0.5 text-slate-400" />
                </div>
                <div className="flex items-center gap-1 mt-1 text-xs text-slate-400 dark:text-slate-500">
                  <Clock size={11} />
                  {formatDate(rev.saved_at)}
                </div>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      {/* ── Main panel: selected review ── */}
      <div className="flex-1 min-w-0">
        {reviewLoading && <LoadingSpinner message="Loading review…" size="lg" />}
        {reviewError && <ErrorBanner message={reviewError} />}

        {!reviewLoading && !reviewError && selectedReview && (
          <LiteratureReview
            markdown={selectedReview.review_markdown}
            topic={selectedReview.topic}
          />
        )}

        {!reviewLoading && !reviewError && !selectedReview && (
          <div className="flex flex-col items-center justify-center h-64 text-slate-400 dark:text-slate-500">
            <BookOpen size={40} strokeWidth={1} className="mb-3 opacity-50" />
            <p>Select a review from the sidebar to read it</p>
          </div>
        )}
      </div>
    </div>
  )
}
