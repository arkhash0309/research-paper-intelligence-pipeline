/**
 * useResearch.js — Custom hook managing the full research pipeline state.
 *
 * Pipeline states (in order):
 *   idle → fetching_papers → analysing → synthesising → done
 *
 * Exposed API:
 *   papers      {object[]}  — normalised paper list from /start
 *   analysis    {object}    — { themes, findings, gaps } from /analyse
 *   review      {object}    — { review_markdown, saved_filepath, filename } from /synthesise
 *   status      {string}    — current pipeline stage
 *   error       {string|null} — last error message or null
 *   runPipeline {function}  — start the full pipeline for a topic
 *   reset       {function}  — reset to idle
 */
import { useState, useCallback } from 'react'
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
  const [papers, setPapers] = useState([])
  const [analysis, setAnalysis] = useState(null)
  const [review, setReview] = useState(null)
  const [status, setStatus] = useState(PIPELINE_STATUS.IDLE)
  const [error, setError] = useState(null)

  /**
   * Run the full pipeline: search → analyse → synthesise.
   *
   * @param {string} topic - The research topic entered by the user
   * @param {number} [maxPapers=10] - Max papers per source
   */
  const runPipeline = useCallback(async (topic, maxPapers = 10) => {
    // Reset state for a fresh run
    setError(null)
    setPapers([])
    setAnalysis(null)
    setReview(null)

    try {
      // Step 1: Fetch papers
      setStatus(PIPELINE_STATUS.FETCHING_PAPERS)
      const searchResult = await startResearch(topic, maxPapers)
      const fetchedPapers = searchResult.papers || []
      setPapers(fetchedPapers)

      // Step 2: Analyse
      setStatus(PIPELINE_STATUS.ANALYSING)
      const analysisResult = await analysePapers(topic, fetchedPapers)
      setAnalysis(analysisResult)

      // Step 3: Synthesise
      setStatus(PIPELINE_STATUS.SYNTHESISING)
      const reviewResult = await synthesiseReview(
        topic,
        fetchedPapers,
        analysisResult.findings,
        analysisResult.gaps
      )
      setReview(reviewResult)

      setStatus(PIPELINE_STATUS.DONE)
    } catch (err) {
      setError(err.message || 'An unexpected error occurred')
      setStatus(PIPELINE_STATUS.IDLE)
    }
  }, [])

  /** Reset all state back to idle */
  const reset = useCallback(() => {
    setPapers([])
    setAnalysis(null)
    setReview(null)
    setStatus(PIPELINE_STATUS.IDLE)
    setError(null)
  }, [])

  return { papers, analysis, review, status, error, runPipeline, reset }
}
