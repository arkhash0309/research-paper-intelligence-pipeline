/**
 * researchApi.js — Axios-based API client for all backend endpoints.
 *
 * Base URL is relative (/api/…) so Vite's proxy forwards requests to
 * http://localhost:8000 during development.
 *
 * All functions throw an Error with a human-readable message on failure.
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 120_000, // Claude API calls can be slow — allow 2 minutes
})

/**
 * POST /api/research/start
 * Search arXiv and Semantic Scholar for papers on the given topic.
 *
 * @param {string} topic - Research topic string
 * @param {number} [maxPapers=10] - Max papers per source
 * @returns {Promise<{papers: object[], total: number, sources: object}>}
 */
export async function startResearch(topic, maxPapers = 10) {
  try {
    const { data } = await api.post('/research/start', {
      topic,
      max_papers: maxPapers,
    })
    return data
  } catch (err) {
    throw new Error(_extractMessage(err, 'Failed to search for papers'))
  }
}

/**
 * POST /api/research/analyse
 * Extract key findings and identify research gaps from a paper list.
 *
 * @param {string} topic - Research topic
 * @param {object[]} papers - Array of normalised paper dicts
 * @returns {Promise<{themes: string[], findings: object, gaps: object}>}
 */
export async function analysePapers(topic, papers) {
  try {
    const { data } = await api.post('/research/analyse', { topic, papers })
    return data
  } catch (err) {
    throw new Error(_extractMessage(err, 'Failed to analyse papers'))
  }
}

/**
 * POST /api/research/synthesise
 * Generate and save a literature review.
 *
 * @param {string} topic - Research topic
 * @param {object[]} papers - Array of normalised paper dicts
 * @param {object} findings - Output from analysePapers
 * @param {object} gaps - Output from analysePapers
 * @returns {Promise<{review_markdown: string, saved_filepath: string, filename: string}>}
 */
export async function synthesiseReview(topic, papers, findings, gaps) {
  try {
    const { data } = await api.post('/research/synthesise', {
      topic,
      papers,
      findings,
      gaps,
    })
    return data
  } catch (err) {
    throw new Error(_extractMessage(err, 'Failed to synthesise literature review'))
  }
}

/**
 * GET /api/research/history
 * List all saved reviews.
 *
 * @returns {Promise<{reviews: object[]}>}
 */
export async function getHistory() {
  try {
    const { data } = await api.get('/research/history')
    return data
  } catch (err) {
    throw new Error(_extractMessage(err, 'Failed to load review history'))
  }
}

/**
 * GET /api/research/review/:filename
 * Load a specific saved review.
 *
 * @param {string} filename - JSON filename of the saved review
 * @returns {Promise<object>} Full review record
 */
export async function getReview(filename) {
  try {
    const { data } = await api.get(`/research/review/${encodeURIComponent(filename)}`)
    return data
  } catch (err) {
    throw new Error(_extractMessage(err, `Failed to load review: ${filename}`))
  }
}

/**
 * Extract a human-readable message from an Axios error.
 *
 * @param {unknown} err - The caught error
 * @param {string} fallback - Message to use if no detail is available
 * @returns {string}
 */
function _extractMessage(err, fallback) {
  if (axios.isAxiosError(err)) {
    return err.response?.data?.detail || err.message || fallback
  }
  return err?.message || fallback
}
