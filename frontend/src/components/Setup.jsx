import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import useInterviewStore from '../store/interviewStore'

const ROLES = ['AI/ML Engineer', 'Backend Engineer', 'Data Scientist']

export default function Setup() {
  const { uploadResume, startSession, setRole, setCandidateName, role, candidateName, resumeData, isLoading, error, setScreen } =
    useInterviewStore()
  const [localName, setLocalName] = useState(candidateName || '')
  const [uploadStatus, setUploadStatus] = useState(null) // null | 'uploading' | 'done' | 'error'

  const onDrop = useCallback(async (files) => {
    if (!files.length) return
    setUploadStatus('uploading')
    const parsed = await uploadResume(files[0])
    if (parsed) {
      setUploadStatus('done')
      setLocalName(parsed.name || localName)
    } else {
      setUploadStatus('error')
    }
  }, [uploadResume, localName])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'text/plain': ['.txt'] },
    maxFiles: 1,
  })

  const canStart = role && (localName || resumeData)

  const handleStart = async () => {
    setCandidateName(localName || resumeData?.name || 'Candidate')
    await startSession()
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12">
      <div className="max-w-xl w-full space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <button onClick={() => setScreen('home')} className="text-gray-500 hover:text-white transition-colors">←</button>
          <div>
            <h2 className="text-2xl font-bold text-white">Setup Your Interview</h2>
            <p className="text-gray-400 text-sm">Upload resume & select role to begin</p>
          </div>
        </div>

        {/* Name */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-300">Your Name</label>
          <input
            type="text"
            value={localName}
            onChange={(e) => setLocalName(e.target.value)}
            placeholder="Enter your name"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Resume upload */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-300">Resume (PDF or TXT)</label>
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
              isDragActive
                ? 'border-indigo-400 bg-indigo-950'
                : uploadStatus === 'done'
                ? 'border-green-500 bg-green-950'
                : 'border-gray-600 hover:border-gray-500 bg-gray-800'
            }`}
          >
            <input {...getInputProps()} />
            {uploadStatus === 'uploading' ? (
              <div className="space-y-2">
                <div className="text-2xl animate-pulse">⏳</div>
                <p className="text-gray-400">Parsing resume...</p>
              </div>
            ) : uploadStatus === 'done' ? (
              <div className="space-y-2">
                <div className="text-2xl">✅</div>
                <p className="text-green-400 font-medium">Resume parsed!</p>
                {resumeData?.skills?.length > 0 && (
                  <p className="text-xs text-gray-400">
                    Skills detected: {resumeData.skills.slice(0, 5).join(', ')}
                    {resumeData.skills.length > 5 ? ` +${resumeData.skills.length - 5} more` : ''}
                  </p>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                <div className="text-3xl">📄</div>
                <p className="text-gray-400">Drag & drop your resume here</p>
                <p className="text-xs text-gray-600">or click to browse · PDF or TXT</p>
              </div>
            )}
          </div>
          {uploadStatus === 'error' && (
            <p className="text-red-400 text-sm">Upload failed. You can continue without a resume.</p>
          )}
        </div>

        {/* Role selection */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-300">Target Role</label>
          <div className="grid grid-cols-1 gap-2">
            {ROLES.map((r) => (
              <button
                key={r}
                onClick={() => setRole(r)}
                className={`py-3 px-4 rounded-lg border text-left transition-colors ${
                  role === r
                    ? 'border-indigo-500 bg-indigo-950 text-indigo-300'
                    : 'border-gray-700 bg-gray-800 text-gray-300 hover:border-gray-600'
                }`}
              >
                <span className="font-medium">{r}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Error */}
        {error && <p className="text-red-400 text-sm bg-red-950 px-4 py-2 rounded-lg">{error}</p>}

        {/* Start button */}
        <button
          onClick={handleStart}
          disabled={!canStart || isLoading}
          className="w-full py-4 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold rounded-xl text-lg transition-colors"
        >
          {isLoading ? '⏳ Starting...' : 'Begin Interview →'}
        </button>
      </div>
    </div>
  )
}
