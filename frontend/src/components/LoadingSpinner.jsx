/**
 * LoadingSpinner.jsx — Animated loading indicator.
 *
 * @param {object} props
 * @param {string} [props.message] - Optional text shown below the spinner
 * @param {'sm'|'md'|'lg'} [props.size='md'] - Spinner size
 */
export default function LoadingSpinner({ message, size = 'md' }) {
  const sizeClasses = {
    sm: 'w-5 h-5 border-2',
    md: 'w-8 h-8 border-3',
    lg: 'w-12 h-12 border-4',
  }

  return (
    <div className="flex flex-col items-center gap-3 py-6">
      {/* Spinning ring using border trick */}
      <div
        className={`${sizeClasses[size]} rounded-full border-accent-200 dark:border-accent-800 border-t-accent-600 dark:border-t-accent-400 animate-spin`}
        role="status"
        aria-label="Loading"
      />
      {message && (
        <p className="text-sm text-slate-500 dark:text-slate-400 animate-pulse">
          {message}
        </p>
      )}
    </div>
  )
}
