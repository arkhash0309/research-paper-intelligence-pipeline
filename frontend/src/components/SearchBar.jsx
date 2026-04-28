/**
 * SearchBar.jsx — Topic input field and search submit button.
 *
 * @param {object} props
 * @param {function} props.onSearch - Called with (topic: string, maxPapers: number)
 * @param {boolean} [props.disabled=false] - Disable input and button during loading
 */
import { useState } from 'react'
import { Search } from 'lucide-react'

export default function SearchBar({ onSearch, disabled = false }) {
  const [topic, setTopic] = useState('')
  const [maxPapers, setMaxPapers] = useState(10)

  function handleSubmit(e) {
    e.preventDefault()
    const trimmed = topic.trim()
    if (!trimmed) return
    onSearch(trimmed, maxPapers)
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      {/* Main search row */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search
            size={18}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
          />
          <input
            type="text"
            value={topic}
            onChange={e => setTopic(e.target.value)}
            disabled={disabled}
            placeholder="e.g. transformer attention mechanisms"
            className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-accent-500 disabled:opacity-50 disabled:cursor-not-allowed transition"
          />
        </div>

        <button
          type="submit"
          disabled={disabled || !topic.trim()}
          className="px-5 py-3 rounded-xl bg-accent-600 hover:bg-accent-700 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
        >
          Find Papers
        </button>
      </div>

      {/* Max papers selector — shown as a small control below the main row */}
      <div className="mt-2 flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <label htmlFor="maxPapers">Papers per source:</label>
        <select
          id="maxPapers"
          value={maxPapers}
          onChange={e => setMaxPapers(Number(e.target.value))}
          disabled={disabled}
          className="bg-transparent border border-slate-200 dark:border-slate-600 rounded px-2 py-0.5 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-1 focus:ring-accent-500 disabled:opacity-50"
        >
          {[5, 10, 15, 20].map(n => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
      </div>
    </form>
  )
}
