import React from 'react'
import useInterviewStore from '../store/interviewStore'

export default function Home() {
  const setScreen = useInterviewStore((s) => s.setScreen)

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="max-w-2xl w-full text-center space-y-8">
        {/* Logo */}
        <div className="space-y-2">
          <div className="text-6xl">🎯</div>
          <h1 className="text-4xl font-bold text-white">
            PG<span className="text-indigo-400">AGI</span>
          </h1>
          <p className="text-xl text-gray-400">AI-Powered Technical Interview Platform</p>
        </div>

        {/* Features */}
        <div className="grid grid-cols-2 gap-4 text-left">
          {[
            { icon: '📄', title: 'Resume-Aware', desc: 'Questions adapt to your skills' },
            { icon: '🧠', title: 'RAG-Grounded', desc: 'Answers sourced from ML textbooks' },
            { icon: '🔄', title: 'Adaptive Flow', desc: '4-stage interview progression' },
            { icon: '📊', title: 'Live Scoring', desc: 'Real-time evaluation & feedback' },
          ].map(({ icon, title, desc }) => (
            <div key={title} className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <div className="text-2xl mb-1">{icon}</div>
              <div className="font-semibold text-white">{title}</div>
              <div className="text-sm text-gray-400">{desc}</div>
            </div>
          ))}
        </div>

        <button
          onClick={() => setScreen('setup')}
          className="w-full py-4 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl text-lg transition-colors"
        >
          Start Interview →
        </button>

        <p className="text-xs text-gray-600">
          Powered by Groq LLaMA-3.3-70B · ChromaDB · all-MiniLM-L6-v2
        </p>
      </div>
    </div>
  )
}
