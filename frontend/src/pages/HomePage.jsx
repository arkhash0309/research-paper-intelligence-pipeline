/**
 * HomePage.jsx — Main search and pipeline page.
 *
 * Layout:
 *   1. Hero section with SearchBar
 *   2. PipelineProgress indicator (visible while pipeline is running)
 *   3. Paper results grid
 *   4. Retry button (resumes from the failed step if the pipeline errors)
 *   5. LiteratureReview panel (appears after synthesis is done)
 */
import { Link } from 'react-router-dom'
import SearchBar from '../components/SearchBar'
import PaperCard from '../components/PaperCard'
import LiteratureReview from '../components/LiteratureReview'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorBanner from '../components/ErrorBanner'
import PipelineProgress from '../components/PipelineProgress'
import { PIPELINE_STATUS } from '../hooks/useResearch'
import { RotateCcw, AlertTriangle } from 'lucide-react'

/** Labels for the retry button, per failed stage */
const RETRY_LABELS = {
  [PIPELINE_STATUS.FETCHING_PAPERS]: 'Retry search',
  [PIPELINE_STATUS.ANALYSING]: 'Retry analysis',
  [PIPELINE_STATUS.SYNTHESISING]: 'Retry writing the review',
}

/** Human-readable loading messages per pipeline stage */
const STAGE_MESSAGES = {
  [PIPELINE_STATUS.FETCHING_PAPERS]: 'Searching arXiv and Semantic Scholar…',
  [PIPELINE_STATUS.ANALYSING]: 'Extracting findings with OpenAI…',
  [PIPELINE_STATUS.SYNTHESISING]: 'Writing your literature review…',
}

/**
 * @param {object} props
 * @param {object} props.research - State and actions from useResearch(), owned by
 *   App so a run survives navigating to Saved Reviews and back.
 */
export default function HomePage({ research }) {
  const {
    topic: currentTopic, papers, analysis, review, status, error, warnings, failedStep,
    runPipeline, retry, dismissError, reset,
  } = research

  const isRunning = status !== PIPELINE_STATUS.IDLE && status !== PIPELINE_STATUS.DONE
  const isDone = status === PIPELINE_STATUS.DONE
  const hasPapers = papers.length > 0

  function handleSearch(topic, maxPapers) {
    runPipeline(topic, maxPapers)
  }

  return (
    <div className="space-y-8">
      {/* ── Hero / Search section ── */}
      <section className="text-center space-y-4 pt-8">
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 dark:text-slate-50">
          Research Paper Intelligence
        </h1>
        <p className="text-slate-500 dark:text-slate-400 max-w-xl mx-auto">
          Enter a research topic and the pipeline will search arXiv & Semantic Scholar,
          extract key findings, and generate a structured literature review — powered by OpenAI.
        </p>
        <SearchBar onSearch={handleSearch} disabled={isRunning} />
      </section>

      {/* ── Error banner ── */}
      {error && (
        <div className="space-y-3">
          <ErrorBanner message={error} onDismiss={dismissError} />
          {failedStep && !isRunning && (
            <div className="flex justify-center">
              <button
                onClick={retry}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent-600 hover:bg-accent-700 text-white font-medium transition-colors"
              >
                <RotateCcw size={16} />
                {RETRY_LABELS[failedStep] || 'Retry'}
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Non-fatal warnings (e.g. one search source unavailable) ── */}
      {warnings.length > 0 && (
        <div
          role="status"
          className="flex items-start gap-3 p-4 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300"
        >
          <AlertTriangle size={18} className="flex-shrink-0 mt-0.5" />
          <ul className="flex-1 text-sm space-y-1">
            {warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}

      {/* ── Pipeline progress steps ── */}
      {status !== PIPELINE_STATUS.IDLE && (
        <PipelineProgress status={status} />
      )}

      {/* ── Loading spinner with stage message ── */}
      {isRunning && (
        <LoadingSpinner message={STAGE_MESSAGES[status]} size="lg" />
      )}

      {/* ── Paper results grid ── */}
      {hasPapers && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">
              {papers.length} papers found
            </h2>
            {!isRunning && (
              <button
                onClick={reset}
                className="flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
              >
                <RotateCcw size={14} /> New search
              </button>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {papers.map((paper, i) => (
              <PaperCard key={paper.id || i} paper={paper} />
            ))}
          </div>

        </section>
      )}

      {/* ── Themes & Gaps summary ── */}
      {analysis && isDone && (
        <section className="grid sm:grid-cols-2 gap-4">
          {/* Themes */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <h3 className="font-semibold mb-3 text-slate-800 dark:text-slate-200">Key Themes</h3>
            <ul className="space-y-1.5">
              {(analysis.themes || []).map((t, i) => (
                <li key={i} className="flex gap-2 text-sm text-slate-600 dark:text-slate-300">
                  <span className="text-accent-500">▸</span> {t}
                </li>
              ))}
            </ul>
          </div>

          {/* Research gaps */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <h3 className="font-semibold mb-3 text-slate-800 dark:text-slate-200">Research Gaps</h3>
            <ul className="space-y-1.5">
              {(analysis.gaps?.gaps || []).map((g, i) => (
                <li key={i} className="flex gap-2 text-sm text-slate-600 dark:text-slate-300">
                  <span className="text-amber-500">?</span> {g}
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {/* ── Literature review output ── */}
      {review && isDone && (
        <section className="space-y-2">
          <LiteratureReview
            markdown={review.review_markdown}
            topic={currentTopic}
          />
          {review.filename && (
            <p className="text-xs text-slate-400 dark:text-slate-500 text-right">
              Saved as{' '}
              <Link
                to={`/reviews/${encodeURIComponent(review.filename)}`}
                className="text-accent-600 dark:text-accent-400 hover:underline"
              >
                <code>{review.filename}</code>
              </Link>
            </p>
          )}
        </section>
      )}
    </div>
  )
}
