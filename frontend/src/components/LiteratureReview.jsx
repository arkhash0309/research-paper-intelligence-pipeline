/**
 * LiteratureReview.jsx — Renders a Markdown literature review with utility actions.
 *
 * Features:
 *   - Renders Markdown as formatted HTML via react-markdown + @tailwindcss/typography
 *   - "Copy to clipboard" button
 *   - "Download as .md" button
 *
 * @param {object} props
 * @param {string} props.markdown - The Markdown review text to render
 * @param {string} [props.topic] - The research topic (used for the download filename)
 */
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Copy, Check, Download } from 'lucide-react'

export default function LiteratureReview({ markdown, topic = 'review' }) {
  const [copied, setCopied] = useState(false)

  /** Copy the raw Markdown to the clipboard */
  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(markdown)
      setCopied(true)
      // Reset the icon after 2 seconds
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback for browsers that block clipboard access
      const el = document.createElement('textarea')
      el.value = markdown
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  /** Trigger a browser download of the Markdown as a .md file */
  function handleDownload() {
    const slug = topic.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')
    const filename = `${slug}-literature-review.md`
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      {/* Action toolbar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
        <span className="text-sm font-medium text-slate-600 dark:text-slate-400">
          Literature Review
        </span>
        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          >
            {copied ? <Check size={13} className="text-green-500" /> : <Copy size={13} />}
            {copied ? 'Copied!' : 'Copy'}
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          >
            <Download size={13} />
            Download .md
          </button>
        </div>
      </div>

      {/* Rendered Markdown — @tailwindcss/typography's `prose` class handles formatting */}
      <div className="p-6 overflow-auto">
        <div className="prose prose-slate dark:prose-invert max-w-none prose-headings:font-semibold prose-a:text-accent-600 dark:prose-a:text-accent-400">
          <ReactMarkdown>{markdown}</ReactMarkdown>
        </div>
      </div>
    </div>
  )
}
