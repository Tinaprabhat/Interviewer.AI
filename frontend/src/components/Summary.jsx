import React from 'react'
import useInterviewStore from '../store/interviewStore'

const RATING_COLOR = {
  Excellent: 'text-green-400',
  Good: 'text-blue-400',
  Average: 'text-yellow-400',
  'Needs Improvement': 'text-red-400',
}

const RECOMMENDATION_COLOR = {
  Hire: 'bg-green-600',
  Consider: 'bg-yellow-600',
  Pass: 'bg-red-700',
}

export default function Summary() {
  const { summary, candidateName, role, reset, fetchSummary, summaryError, llmProvider } = useInterviewStore()

  const providerLabel =
    llmProvider === 'ollama' ? 'Ollama Mistral' :
    llmProvider === 'fallback' ? 'Fallback (no LLM)' :
    'Groq LLaMA-3.3-70B'

  if (!summary) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          {summaryError ? (
            <>
              <div className="text-3xl">⚠️</div>
              <p className="text-red-400 text-sm max-w-xs">{summaryError}</p>
              <div className="flex gap-3 justify-center">
                <button
                  onClick={fetchSummary}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm rounded-lg transition-colors"
                >
                  Retry
                </button>
                <button
                  onClick={reset}
                  className="px-5 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors"
                >
                  New Interview
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="text-3xl animate-spin">⏳</div>
              <p className="text-gray-400">Generating your interview summary...</p>
            </>
          )}
        </div>
      </div>
    )
  }

  const score = summary.score_out_of_10 || 0
  const scoreColor = score >= 8 ? 'text-green-400' : score >= 6 ? 'text-yellow-400' : 'text-red-400'

  return (
    <div className="min-h-screen px-4 py-12">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="text-4xl">📋</div>
          <h1 className="text-2xl font-bold text-white">Interview Complete</h1>
          <p className="text-gray-400">{candidateName} — {role}</p>
        </div>

        {/* Score card */}
        <div className="bg-gray-800 border border-gray-700 rounded-2xl p-6 text-center space-y-3">
          <div className={`text-6xl font-bold ${scoreColor}`}>{score}<span className="text-3xl text-gray-500">/10</span></div>
          <div className={`text-xl font-semibold ${RATING_COLOR[summary.overall_rating] || 'text-gray-300'}`}>
            {summary.overall_rating}
          </div>
          <div className={`inline-block px-4 py-1 rounded-full text-white text-sm font-medium ${RECOMMENDATION_COLOR[summary.recommendation] || 'bg-gray-600'}`}>
            {summary.recommendation}
          </div>
          <p className="text-gray-300 text-sm mt-2">{summary.summary_paragraph}</p>
        </div>

        {/* Strengths & Improvements */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-800 border border-green-800 rounded-xl p-4 space-y-2">
            <h3 className="text-green-400 font-semibold text-sm">✅ Strengths</h3>
            <ul className="space-y-1">
              {(summary.strengths || []).map((s, i) => (
                <li key={i} className="text-gray-300 text-sm">• {s}</li>
              ))}
            </ul>
          </div>
          <div className="bg-gray-800 border border-orange-800 rounded-xl p-4 space-y-2">
            <h3 className="text-orange-400 font-semibold text-sm">📈 To Improve</h3>
            <ul className="space-y-1">
              {(summary.improvements || []).map((s, i) => (
                <li key={i} className="text-gray-300 text-sm">• {s}</li>
              ))}
            </ul>
          </div>
        </div>

        {/* Stats */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-xl font-bold text-white">{summary.total_questions || 0}</div>
              <div className="text-xs text-gray-500">Questions</div>
            </div>
            <div>
              <div className="text-xl font-bold text-white">{score}</div>
              <div className="text-xs text-gray-500">Avg Score</div>
            </div>
            <div>
              <div className="text-xl font-bold text-white">{summary.recommendation}</div>
              <div className="text-xs text-gray-500">Decision</div>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={reset}
            className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-xl transition-colors"
          >
            New Interview
          </button>
        </div>

        <p className="text-xs text-gray-600 text-center">
          Questions grounded via RAG from ML textbooks · Evaluated by {providerLabel}
        </p>
      </div>
    </div>
  )
}
