import axios from 'axios'

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL

console.log('API_BASE_URL:', API_BASE_URL)

const client = axios.create({
  baseURL: API_BASE_URL,
})

// Intercept responses to unwrap .data and normalize errors
client.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error('API request failed', {
      baseURL: API_BASE_URL,
      url: err.config?.url,
      method: err.config?.method,
      status: err.response?.status,
      response: err.response?.data,
    })

    const message =
      err.response?.data?.detail ||
      err.message ||
      'Unknown error'

    return Promise.reject(new Error(message))
  }
)

// ── Resume ────────────────────────────────────────────────────────────────────

export const uploadResume = (file) => {
  const form = new FormData()
  form.append('file', file)

  return client
    .post('/api/resume/upload', form)
    .then((r) => r.data)
}

export const getResume = (resumeId) =>
  client
    .get(`/api/resume/${resumeId}`)
    .then((r) => r.data)

// ── Sessions ──────────────────────────────────────────────────────────────────

export const createSession = ({
  role,
  candidateName,
  resumeId,
  resumeData,
}) =>
  client
    .post('/api/sessions/create', {
      role,
      candidate_name: candidateName,
      resume_id: resumeId ?? null,
      resume_data: resumeData ?? null,
    })
    .then((r) => r.data)

export const getSession = (sessionId) =>
  client
    .get(`/api/sessions/${sessionId}`)
    .then((r) => r.data)

export const getSessionHistory = (sessionId) =>
  client
    .get(`/api/sessions/${sessionId}/history`)
    .then((r) => r.data)

export const getSessionSummary = (sessionId) =>
  client
    .get(`/api/sessions/${sessionId}/summary`)
    .then((r) => r.data)

// ── Interview ─────────────────────────────────────────────────────────────────

export const fetchNextQuestion = (sessionId) =>
  client
    .post(`/api/interview/${sessionId}/next`)
    .then((r) => r.data)

export const submitAnswer = (
  sessionId,
  answer,
  questionData
) =>
  client
    .post(`/api/interview/${sessionId}/answer`, {
      answer,
      question_data: questionData ?? null,
    })
    .then((r) => r.data)

export const getInterviewStatus = (sessionId) =>
  client
    .get(`/api/interview/${sessionId}/status`)
    .then((r) => r.data)

// ── Utility ───────────────────────────────────────────────────────────────────

export const getRoles = () =>
  client
    .get('/api/roles')
    .then((r) => r.data)

export const healthCheck = () =>
  client
    .get('/api/health')
    .then((r) => r.data)