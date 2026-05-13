import React, { useState, useRef, useEffect } from 'react'
import useInterviewStore from '../store/interviewStore'

const STEP_COLORS = {
  'warmup': 'text-blue-400',
  'core': 'text-yellow-400',
  'deep_dive': 'text-orange-400',
  'scenario': 'text-purple-400',
  'closing': 'text-green-400',
}

const STEP_LABELS = {
  warmup: '🌡️ Warm-up',
  core: '⚙️ Core',
  deep_dive: '🔍 Deep Dive',
  scenario: '🏗️ Scenario',
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  const isSystem = msg.role === 'system'
  const isInterviewer = msg.role === 'interviewer'
  const isFeedback = msg.role === 'feedback'

  if (isSystem) {
    return (
      <div className="flex justify-center my-4">
        <div className="bg-gray-800 border border-gray-700 rounded-xl px-5 py-4 max-w-lg text-sm text-gray-300 text-center whitespace-pre-line">
          {msg.content}
        </div>
      </div>
    )
  }

  if (isInterviewer) {
    return (
      <div className="flex gap-3 mb-4">
        <div className="w-9 h-9 bg-indigo-600 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0">
          AI
        </div>
        <div className="flex-1 max-w-2xl">
          {msg.meta && (
            <div className="flex gap-2 mb-1 text-xs text-gray-500">
              <span>Q{msg.meta.questionNumber}</span>
              <span>·</span>
              <span className={STEP_COLORS[msg.meta.step?.toLowerCase().replace(/[🌡️⚙️🔍🏗️]\s/, '')] || 'text-gray-400'}>
                {msg.meta.step}
              </span>
              <span>·</span>
              <span className="capitalize">{msg.meta.difficulty}</span>
              {msg.meta.topic && <><span>·</span><span className="text-indigo-400">{msg.meta.topic}</span></>}
            </div>
          )}
          <div className="bg-gray-800 border border-gray-700 rounded-2xl rounded-tl-sm px-4 py-3 text-white">
            {msg.content}
          </div>
        </div>
      </div>
    )
  }

  if (isUser) {
    return (
      <div className="flex gap-3 mb-4 justify-end">
        <div className="max-w-xl bg-indigo-600 rounded-2xl rounded-tr-sm px-4 py-3 text-white">
          {msg.content}
        </div>
        <div className="w-9 h-9 bg-gray-700 rounded-full flex items-center justify-center text-white text-sm shrink-0">
          You
        </div>
      </div>
    )
  }

  if (isFeedback) {
    const score = msg.meta?.score || 0
    const color = score >= 8 ? 'border-green-600 bg-green-950' : score >= 5 ? 'border-yellow-600 bg-yellow-950' : 'border-red-700 bg-red-950'
    return (
      <div className={`border rounded-xl px-4 py-3 mb-4 ml-12 max-w-2xl text-sm text-gray-300 whitespace-pre-line ${color}`}>
        {msg.content}
      </div>
    )
  }

  return null
}

export default function Chat() {
  const {
    messages, submitAnswer, isLoading, isComplete, currentStep,
    questionNumber, role, candidateName, error, setError,
  } = useInterviewStore()

  const [input, setInput] = useState('')
  const endRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading || isComplete) return
    const text = input.trim()
    setInput('')
    try {
      await submitAnswer(text)
    } catch {
      setInput(text)
    }
    inputRef.current?.focus()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const totalQ = 5
  const progress = Math.min((questionNumber / totalQ) * 100, 100)

  return (
    <div className="h-screen flex flex-col bg-gray-950">
      {/* Header */}
      <div className="border-b border-gray-800 px-6 py-3 flex items-center gap-4">
        <div className="flex-1">
          <div className="text-sm font-semibold text-white">{candidateName} — {role}</div>
          <div className="text-xs text-gray-500">
            {STEP_LABELS[currentStep] || currentStep} · Q{questionNumber}/{totalQ}
          </div>
        </div>
        <div className="w-40">
          <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-500 transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-1 scrollbar-thin">
        {messages.map((msg, i) => (
          <MessageBubble key={i} msg={msg} />
        ))}
        {isLoading && (
          <div className="flex gap-3 mb-4">
            <div className="w-9 h-9 bg-indigo-600 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0">
              AI
            </div>
            <div className="bg-gray-800 border border-gray-700 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Error banner */}
      {error && (
        <div className="border-t border-red-800 bg-red-950 px-6 py-2 flex items-center justify-between">
          <span className="text-red-400 text-sm">{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200 text-lg leading-none ml-4">✕</button>
        </div>
      )}

      {/* Input */}
      {!isComplete && (
        <div className="border-t border-gray-800 px-6 py-4">
          <div className="flex gap-3 items-end">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your answer... (Enter to send, Shift+Enter for newline)"
              disabled={isLoading}
              rows={3}
              className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 resize-none text-sm disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="px-5 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-colors"
            >
              Send
            </button>
          </div>
          <p className="text-xs text-gray-600 mt-2 text-center">
            Answers are evaluated for concept coverage against ML textbook knowledge base
          </p>
        </div>
      )}
    </div>
  )
}
