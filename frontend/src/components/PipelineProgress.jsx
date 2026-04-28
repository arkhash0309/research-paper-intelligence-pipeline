/**
 * PipelineProgress.jsx — Step-by-step progress indicator for the pipeline run.
 *
 * Shows four steps: Search → Analyse → Synthesise → Done.
 * Highlights the current step and marks completed steps with a check.
 *
 * @param {object} props
 * @param {string} props.status - Current pipeline status string (from PIPELINE_STATUS)
 */
import { Check, Search, Brain, FileText, CheckCircle } from 'lucide-react'
import { PIPELINE_STATUS } from '../hooks/useResearch'

const STEPS = [
  { key: PIPELINE_STATUS.FETCHING_PAPERS, label: 'Searching papers', icon: Search },
  { key: PIPELINE_STATUS.ANALYSING,       label: 'Analysing with AI', icon: Brain },
  { key: PIPELINE_STATUS.SYNTHESISING,    label: 'Writing review',    icon: FileText },
  { key: PIPELINE_STATUS.DONE,            label: 'Complete',          icon: CheckCircle },
]

const STATUS_ORDER = [
  PIPELINE_STATUS.IDLE,
  PIPELINE_STATUS.FETCHING_PAPERS,
  PIPELINE_STATUS.ANALYSING,
  PIPELINE_STATUS.SYNTHESISING,
  PIPELINE_STATUS.DONE,
]

export default function PipelineProgress({ status }) {
  if (status === PIPELINE_STATUS.IDLE) return null

  const currentIndex = STATUS_ORDER.indexOf(status)

  return (
    <div className="flex items-center gap-1 justify-center flex-wrap sm:gap-3 py-4">
      {STEPS.map((step, i) => {
        // Step indices: fetching=1, analysing=2, synthesising=3, done=4
        const stepStatusIndex = STATUS_ORDER.indexOf(step.key)
        const isComplete = currentIndex > stepStatusIndex
        const isCurrent = currentIndex === stepStatusIndex
        const isPending = currentIndex < stepStatusIndex

        const Icon = step.icon

        return (
          <div key={step.key} className="flex items-center gap-1 sm:gap-3">
            {/* Step circle */}
            <div className={`
              flex items-center gap-2 px-3 py-1.5 rounded-full text-sm transition-all
              ${isComplete
                ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                : isCurrent
                  ? 'bg-accent-100 dark:bg-accent-900/30 text-accent-700 dark:text-accent-400 animate-pulse'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-600'
              }
            `}>
              {isComplete
                ? <Check size={14} />
                : <Icon size={14} />
              }
              <span className="hidden sm:inline font-medium text-xs">{step.label}</span>
            </div>

            {/* Connector line between steps */}
            {i < STEPS.length - 1 && (
              <div className={`hidden sm:block h-px w-8 transition-colors ${
                isComplete ? 'bg-green-300 dark:bg-green-700' : 'bg-slate-200 dark:bg-slate-700'
              }`} />
            )}
          </div>
        )
      })}
    </div>
  )
}
