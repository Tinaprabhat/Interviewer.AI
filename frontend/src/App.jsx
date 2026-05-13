import React from 'react'
import useInterviewStore from './store/interviewStore'
import Home from './components/Home'
import Setup from './components/Setup'
import Chat from './components/Chat'
import Summary from './components/Summary'

export default function App() {
  const screen = useInterviewStore((s) => s.screen)

  return (
    <div className="bg-gray-950 min-h-screen text-white">
      {screen === 'home' && <Home />}
      {screen === 'setup' && <Setup />}
      {screen === 'interview' && <Chat />}
      {screen === 'summary' && <Summary />}
    </div>
  )
}
