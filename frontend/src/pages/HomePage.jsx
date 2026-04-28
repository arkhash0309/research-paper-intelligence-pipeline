/**
 * HomePage.jsx — Main search and pipeline page.
 *
 * Layout:
 *   1. Hero section with SearchBar
 *   2. PipelineProgress indicator (visible while pipeline is running)
 *   3. Paper results grid
 *   4. "Analyse & Synthesise" button (appears after papers are fetched)
 *   5. LiteratureReview panel (appears after synthesis is done)
 */
import { useState } from 'react'
import SearchBar from '../components/SearchBar'
import PaperCard from '../components/PaperCard'
import LiteratureReview from '../components/LiteratureReview'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorBanner from '../components/ErrorBanner'
import PipelineProgress from '../components/PipelineProgress'
import useResearch, { PIPELINE_STATUS } from '../hooks/useResearch'
import { Sparkles, RotateCcw } from 'lucide-react'

/** Human-readable loading messages per pipeline stage */
const STAGE_MESSAGES = {
  [PIPELINE_STATUS.FETCHING_PAPERS]: 'Searching arXiv and Semantic Scholar…',
  [PIPELINE_STATUS.ANALYSING]: 'Extracting findings with Claude AI…',
  [PIPELINE_STATUS.SYNTHESISING]: 'Writing your literature review…',
}

export default function HomePage() {
  const { papers, analysis, review, status, error, runPipeline, reset } = useResearch()
  const [currentTopic, setCurrentTopic] = useState('')

  const isRunning = status !== PIPELINE_STATUS.IDLE && status !== PIPELINE_STATUS.DONE
  const isDone = status === PIPELINE_STATUS.DONE
  const hasPapers = papers.length > 0

  function handleSearch(topic, maxPapers) {
    setCurrentTopic(topic)
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
          extract key findings, and generate a structured literature review — all with Claude AI.
        </p>
        <SearchBar onSearch={handleSearch} disabled={isRunning} />
      </section>

      {/* ── Error banner ── */}
      {error && (
        <ErrorBanner message={error} onDismiss={reset} />
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
            {isDone && (
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

          {/* "Analyse & Synthesise" button — shown after papers load but pipeline is idle */}
          {status === PIPELINE_STATUS.IDLE && hasPapers && !isDone && (
            <div className="flex justify-center pt-2">
              <button
                onClick={() => runPipeline(currentTopic)}
                className="flex items-center gap-2 px-6 py-3 rounded-xl bg-accent-600 hover:bg-accent-700 text-white font-medium transition-colors"
              >
                <Sparkles size={18} />
                Analyse &amp; Synthesise
              </button>
            </div>
          )}
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
              Saved as <code>{review.filename}</code>
            </p>
          )}
        </section>
      )}
    </div>
  )
}
