/**
 * useResearch.js — Custom hook managing the full research pipeline state.
 *
 * Pipeline states (in order):
 *   idle → fetching_papers → analysing → synthesising → done
 *
 * Exposed API:
 *   topic       {string}    — topic of the current/last run
 *   papers      {object[]}  — normalised paper list from /start
 *   analysis    {object}    — { themes, findings, gaps } from /analyse
 *   review      {object}    — { review_markdown, saved_filepath, filename } from /synthesise
 *   status      {string}    — current pipeline stage
 *   error       {string|null} — last error message or null
 *   warnings    {string[]}  — non-fatal problems (e.g. one search source failed)
 *   failedStep  {string|null} — pipeline stage that failed and can be retried
 *   runPipeline {function}  — start the full pipeline for a topic
 *   retry       {function}  — resume the pipeline from the step that failed
 *   dismissError {function} — hide the error without discarding results
 *   reset       {function}  — reset to idle
 */
import { useState, useCallback, useRef } from 'react'
import { startResearch, analysePapers, synthesiseReview } from '../api/researchApi'

/** All possible pipeline status values */
export const PIPELINE_STATUS = {
  IDLE: 'idle',
  FETCHING_PAPERS: 'fetching_papers',
  ANALYSING: 'analysing',
  SYNTHESISING: 'synthesising',
  DONE: 'done',
}

export default function useResearch() {
  const [topic, setTopic] = useState('')
  const [papers, setPapers] = useState([])
  const [analysis, setAnalysis] = useState(null)
  const [review, setReview] = useState(null)
  const [status, setStatus] = useState(PIPELINE_STATUS.IDLE)
  const [error, setError] = useState(null)
  const [warnings, setWarnings] = useState([])
  const [failedStep, setFailedStep] = useState(null)

  // Inputs and intermediate results of the current run, kept in a ref so a
  // retry can resume from the failed step without re-running earlier ones.
  const runRef = useRef({ topic: '', maxPapers: 10, papers: [], analysis: null })

  /**
   * Execute the pipeline starting at `fromStep`, reusing results of earlier
   * steps stored in runRef.
   */
  const execute = useCallback(async (fromStep) => {
    const run = runRef.current
    let step = fromStep
    setError(null)
    setFailedStep(null)

    try {
      // Step 1: Fetch papers
      if (step === PIPELINE_STATUS.FETCHING_PAPERS) {
        setStatus(step)
        const searchResult = await startResearch(run.topic, run.maxPapers)
        const fetchedPapers = searchResult.papers || []
        run.papers = fetchedPapers
        setPapers(fetchedPapers)
        setWarnings(searchResult.warnings || [])

        // Nothing to analyse — stop here instead of asking the model to review nothing
        if (fetchedPapers.length === 0) {
          setError(`No papers found for "${run.topic}". Try a broader or differently worded topic.`)
          setStatus(PIPELINE_STATUS.IDLE)
          return
        }
        step = PIPELINE_STATUS.ANALYSING
      }

      // Step 2: Analyse
      if (step === PIPELINE_STATUS.ANALYSING) {
        setStatus(step)
        const analysisResult = await analysePapers(run.topic, run.papers)
        run.analysis = analysisResult
        setAnalysis(analysisResult)
        step = PIPELINE_STATUS.SYNTHESISING
      }

      // Step 3: Synthesise
      if (step === PIPELINE_STATUS.SYNTHESISING) {
        setStatus(step)
        const reviewResult = await synthesiseReview(
          run.topic,
          run.papers,
          run.analysis.findings,
          run.analysis.gaps
        )
        setReview(reviewResult)
      }

      setStatus(PIPELINE_STATUS.DONE)
    } catch (err) {
      setError(err.message || 'An unexpected error occurred')
      setFailedStep(step)
      setStatus(PIPELINE_STATUS.IDLE)
    }
  }, [])

  /**
   * Run the full pipeline: search → analyse → synthesise.
   *
   * @param {string} topic - The research topic entered by the user
   * @param {number} [maxPapers=10] - Max papers per source
   */
  const runPipeline = useCallback((topic, maxPapers = 10) => {
    runRef.current = { topic, maxPapers, papers: [], analysis: null }
    setTopic(topic)
    setWarnings([])
    setPapers([])
    setAnalysis(null)
    setReview(null)
    return execute(PIPELINE_STATUS.FETCHING_PAPERS)
  }, [execute])

  /** Resume from the step that failed, keeping results from earlier steps */
  const retry = useCallback(() => {
    if (failedStep) return execute(failedStep)
  }, [execute, failedStep])

  /** Hide the error banner but keep any papers/analysis already fetched */
  const dismissError = useCallback(() => {
    setError(null)
  }, [])

  /** Reset all state back to idle */
  const reset = useCallback(() => {
    runRef.current = { topic: '', maxPapers: 10, papers: [], analysis: null }
    setTopic('')
    setPapers([])
    setAnalysis(null)
    setReview(null)
    setStatus(PIPELINE_STATUS.IDLE)
    setError(null)
    setWarnings([])
    setFailedStep(null)
  }, [])

  return {
    topic, papers, analysis, review, status, error, warnings, failedStep,
    runPipeline, retry, dismissError, reset,
  }
}
