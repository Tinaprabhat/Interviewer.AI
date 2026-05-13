import { create } from 'zustand'
import * as api from '../api'

const useInterviewStore = create((set, get) => ({
  // ── State ───────────────────────────────────────────────────────────────────
  screen: 'home', // home | setup | interview | summary
  role: '',
  candidateName: '',
  resumeData: null,
  resumeId: null,
  sessionId: null,
  messages: [],
  isLoading: false,
  error: null,
  currentQuestion: null,
  questionNumber: 0,
  currentStep: 'warmup',
  isComplete: false,
  summary: null,
  summaryError: null,
  llmProvider: null,

  // ── Setters ─────────────────────────────────────────────────────────────────
  setScreen: (screen) => set({ screen }),
  setRole: (role) => set({ role }),
  setCandidateName: (name) => set({ candidateName: name }),
  setError: (err) => set({ error: err }),

  // ── Upload resume ────────────────────────────────────────────────────────────
  uploadResume: async (file) => {
    set({ isLoading: true, error: null })
    try {
      const data = await api.uploadResume(file)
      const parsed = data.parsed
      // Store both resumeId and resumeData so startSession can send both
      set({
        resumeData: parsed,
        resumeId: data.resume_id,
        candidateName: parsed.name || get().candidateName || 'Candidate',
        isLoading: false,
      })
      return parsed
    } catch (e) {
      set({ isLoading: false, error: e.message || 'Resume upload failed' })
      return null
    }
  },

  // ── Start session ─────────────────────────────────────────────────────────────
  // Always forwards BOTH resume_id (DB reference) and resume_data (inline parsed
  // JSON) so the backend can use whichever is available without an extra lookup.
  startSession: async () => {
    const { role, candidateName, resumeData, resumeId } = get()
    set({ isLoading: true, error: null })
    try {
      const data = await api.createSession({
        role,
        candidateName,
        resumeId,
        resumeData,
      })
      set({
        sessionId: data.session_id,
        isLoading: false,
        screen: 'interview',
        messages: [
          {
            role: 'system',
            content: `👋 Welcome ${candidateName}! I'm your AI interviewer for the **${role}** position.\n\nThis is a structured technical interview with 5 questions across 4 stages: Warm-up → Core Technical → Deep Dive → Scenario.\n\nLet's begin!`,
          },
        ],
      })
      await get().fetchNextQuestion()
    } catch (e) {
      set({ isLoading: false, error: e.message || 'Failed to start session' })
    }
  },

  // ── Fetch next question ────────────────────────────────────────────────────────
  fetchNextQuestion: async () => {
    const { sessionId } = get()
    if (!sessionId) return
    set({ isLoading: true, error: null })
    try {
      const data = await api.fetchNextQuestion(sessionId)
      if (data.is_complete) {
        await get().fetchSummary()
        return
      }
      const stepLabel = {
        warmup: '🌡️ Warm-up',
        core: '⚙️ Core Technical',
        deep_dive: '🔍 Deep Dive',
        scenario: '🏗️ Scenario',
      }[data.step] || data.step

      set((state) => ({
        isLoading: false,
        currentQuestion: data,
        questionNumber: data.question_number,
        currentStep: data.step,
        llmProvider: data.llm_provider || state.llmProvider,
        messages: [
          ...state.messages,
          {
            role: 'interviewer',
            content: data.question,
            meta: {
              questionNumber: data.question_number,
              step: stepLabel,
              difficulty: data.difficulty,
              topic: data.topic,
            },
          },
        ],
      }))
    } catch (e) {
      set({ isLoading: false, error: e.message || 'Failed to fetch question' })
    }
  },

  // ── Submit answer ──────────────────────────────────────────────────────────────
  submitAnswer: async (answer) => {
    const { sessionId } = get()
    if (!sessionId || !answer.trim()) return

    set((state) => ({
      messages: [...state.messages, { role: 'user', content: answer }],
      isLoading: true,
      error: null,
    }))

    try {
      const data = await api.submitAnswer(sessionId, answer, get().currentQuestion)
      const eval_ = data.evaluation
      const qualityEmoji = {
        excellent: '🌟',
        good: '✅',
        partial: '⚠️',
        poor: '❌',
        no_answer: '🔇',
      }[eval_?.quality] || ''

      let feedbackContent = `${qualityEmoji} **Score: ${eval_?.score}/10** — ${eval_?.feedback}`
      if (eval_?.missed_concepts?.length) {
        feedbackContent += `\n\n💡 *Missed concepts: ${eval_.missed_concepts.join(', ')}*`
      }
      if (data.follow_up && eval_?.quality !== 'excellent') {
        feedbackContent += `\n\n🔄 *Follow-up: ${data.follow_up}*`
      }

      set((state) => ({
        isLoading: false,
        isComplete: data.is_complete,
        currentStep: data.current_step,
        messages: [
          ...state.messages,
          {
            role: 'feedback',
            content: feedbackContent,
            meta: { score: eval_?.score, quality: eval_?.quality },
          },
        ],
      }))

      if (data.is_complete) {
        set((state) => ({
          messages: [
            ...state.messages,
            {
              role: 'system',
              content: `Thank you, ${get().candidateName}! Your interview is now complete. Generating your results...`,
            },
          ],
        }))
        await get().fetchSummary()
      } else {
        setTimeout(() => get().fetchNextQuestion(), 800)
      }

      return data
    } catch (e) {
      console.error('Failed to submit answer', e)
      set({ isLoading: false, error: e.message || 'Failed to submit answer' })
    }
  },

  // ── Fetch summary ──────────────────────────────────────────────────────────────
  fetchSummary: async () => {
    const { sessionId } = get()
    if (!sessionId) return
    set({ summaryError: null, isLoading: true })

    const attempt = async () => {
      const data = await api.getSessionSummary(get().sessionId)
      set({ summary: data, screen: 'summary', isComplete: true, isLoading: false, summaryError: null })
    }

    try {
      await attempt()
    } catch {
      // Summary may still be generating — wait 2 s then try once more
      await new Promise((r) => setTimeout(r, 2000))
      try {
        await attempt()
      } catch {
        set({
          isLoading: false,
          screen: 'summary',
          summaryError: 'Summary generation failed. Please try again.',
        })
      }
    }
  },

  // ── Reset ──────────────────────────────────────────────────────────────────────
  reset: () =>
    set({
      screen: 'home',
      role: '',
      candidateName: '',
      resumeData: null,
      resumeId: null,
      sessionId: null,
      messages: [],
      isLoading: false,
      error: null,
      currentQuestion: null,
      questionNumber: 0,
      currentStep: 'warmup',
      isComplete: false,
      summary: null,
      summaryError: null,
      llmProvider: null,
    }),
}))

export default useInterviewStore
