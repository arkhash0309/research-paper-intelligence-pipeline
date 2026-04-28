/**
 * ErrorBanner.jsx — Dismissible error message banner.
 *
 * @param {object} props
 * @param {string} props.message - Error message to display
 * @param {function} [props.onDismiss] - Called when the user closes the banner
 */
import { AlertCircle, X } from 'lucide-react'

export default function ErrorBanner({ message, onDismiss }) {
  if (!message) return null

  return (
    <div
      role="alert"
      className="flex items-start gap-3 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400"
    >
      <AlertCircle size={18} className="flex-shrink-0 mt-0.5" />
      <p className="flex-1 text-sm">{message}</p>

      {/* Dismiss button — only shown if onDismiss is provided */}
      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="Dismiss error"
          className="flex-shrink-0 text-red-400 hover:text-red-600 dark:hover:text-red-200 transition-colors"
        >
          <X size={16} />
        </button>
      )}
    </div>
  )
}
