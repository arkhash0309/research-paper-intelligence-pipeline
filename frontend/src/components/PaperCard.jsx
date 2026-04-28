/**
 * PaperCard.jsx — Displays a single academic paper with expandable abstract.
 *
 * @param {object} props
 * @param {object} props.paper - Normalised paper dict from the API
 * @param {string} props.paper.title
 * @param {string} props.paper.authors
 * @param {number|null} props.paper.year
 * @param {string} props.paper.abstract
 * @param {string} props.paper.source — 'arxiv' | 'semantic_scholar'
 * @param {string} props.paper.url
 * @param {string} props.paper.pdf_url
 * @param {number} props.paper.citation_count
 */
import { useState } from 'react'
import { ChevronDown, ChevronUp, ExternalLink, FileText, BookOpen } from 'lucide-react'

/** Badge colour per source */
const SOURCE_STYLES = {
  arxiv: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  semantic_scholar: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
}
const SOURCE_LABELS = {
  arxiv: 'arXiv',
  semantic_scholar: 'Semantic Scholar',
}

export default function PaperCard({ paper }) {
  const [expanded, setExpanded] = useState(false)

  const sourceStyle = SOURCE_STYLES[paper.source] || 'bg-slate-100 text-slate-600'
  const sourceLabel = SOURCE_LABELS[paper.source] || paper.source

  return (
    <article className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 hover:shadow-md dark:hover:shadow-slate-700/30 transition-shadow">
      {/* Header row: source badge + citation count */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${sourceStyle}`}>
          {sourceLabel}
        </span>
        {paper.citation_count > 0 && (
          <span className="text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1">
            <BookOpen size={12} />
            {paper.citation_count.toLocaleString()} citations
          </span>
        )}
      </div>

      {/* Title — links to the paper landing page */}
      <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-1 leading-snug">
        {paper.url ? (
          <a
            href={paper.url}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-accent-600 dark:hover:text-accent-400 transition-colors"
          >
            {paper.title}
          </a>
        ) : (
          paper.title
        )}
      </h3>

      {/* Authors + year */}
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-3">
        {paper.authors}
        {paper.year ? ` · ${paper.year}` : ''}
      </p>

      {/* Expandable abstract */}
      {paper.abstract && (
        <>
          {expanded && (
            <p className="text-sm text-slate-600 dark:text-slate-300 mb-3 leading-relaxed">
              {paper.abstract}
            </p>
          )}
          <button
            onClick={() => setExpanded(v => !v)}
            className="flex items-center gap-1 text-xs text-accent-600 dark:text-accent-400 hover:underline transition-colors"
          >
            {expanded ? (
              <>
                <ChevronUp size={14} /> Hide abstract
              </>
            ) : (
              <>
                <ChevronDown size={14} /> Show abstract
              </>
            )}
          </button>
        </>
      )}

      {/* Footer links */}
      <div className="flex gap-3 mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
        {paper.url && (
          <a
            href={paper.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 hover:text-accent-600 dark:hover:text-accent-400 transition-colors"
          >
            <ExternalLink size={12} /> View paper
          </a>
        )}
        {paper.pdf_url && (
          <a
            href={paper.pdf_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 hover:text-accent-600 dark:hover:text-accent-400 transition-colors"
          >
            <FileText size={12} /> PDF
          </a>
        )}
      </div>
    </article>
  )
}
