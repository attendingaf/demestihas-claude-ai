'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import LcarsHeader from '@/components/lcars/LcarsHeader'
import LcarsSidebar from '@/components/lcars/LcarsSidebar'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const router = useRouter()

  // Check authentication on mount
  useEffect(() => {
    const token = localStorage.getItem('jwt_token')
    if (!token) {
      router.push('/login')
    } else {
      setIsAuthenticated(true)
    }
  }, [router])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const token = localStorage.getItem('jwt_token')
      const userId = localStorage.getItem('user_id') || 'executive_mene'

      const response = await axios.post('/api/chat', {
        message: input,
        user_id: userId,
        chat_id: `chat_${Date.now()}`
      }, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date().toISOString()
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error: any) {
      console.error('Error sending message:', error)

      // If 401, redirect to login
      if (error.response?.status === 401) {
        localStorage.removeItem('jwt_token')
        localStorage.removeItem('user_id')
        router.push('/login')
        return
      }

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Error: Unable to connect to agent service.',
        timestamp: new Date().toISOString()
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // Show loading while checking authentication
  if (!isAuthenticated) {
    return (
      <div className="h-screen w-screen bg-black flex items-center justify-center">
        <div className="text-lcars-orange text-4xl font-antonio font-bold tracking-widest animate-pulse">
          INITIALIZING...
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen w-screen bg-black overflow-hidden flex flex-col p-2 gap-2">

      {/* REGION 1: Header */}
      <LcarsHeader />

      <div className="flex-1 flex overflow-hidden gap-2">

        {/* REGION 2: Sidebar */}
        <LcarsSidebar />

        {/* REGION 3: Main Content (Framed Viewscreen) */}
        <main className="flex-1 flex flex-col relative">

          {/* Top Frame Border */}
          <div className="h-4 w-full bg-lcars-gold rounded-tl-[20px] rounded-tr-[20px] mb-1 opacity-80"></div>

          {/* Viewport */}
          <div className="flex-1 bg-black border-l-4 border-r-4 border-lcars-gold/30 relative overflow-hidden rounded-[20px] shadow-[inset_0_0_50px_rgba(255,156,40,0.1)]">

            {/* Messages Area */}
            <div className="absolute inset-0 overflow-y-auto p-8 space-y-6 scroll-smooth">
              {messages.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center select-none opacity-40">
                  <div className="text-lcars-orange text-8xl font-antonio font-bold tracking-widest mb-4">LCARS 24</div>
                  <div className="text-lcars-gold text-xl tracking-[0.5em]">READY FOR INPUT</div>

                  {/* Decorative lines */}
                  <div className="w-96 h-1 bg-lcars-orange mt-8 relative">
                    <div className="absolute -top-1 left-0 w-2 h-3 bg-lcars-orange"></div>
                    <div className="absolute -top-1 right-0 w-2 h-3 bg-lcars-orange"></div>
                  </div>
                </div>
              )}

              {messages.map((message, index) => (
                <div key={index} className={`max-w-3xl ${message.role === 'user' ? 'ml-auto' : 'mr-auto'}`}>
                  <div className={`p-6 rounded-[20px] border-2 ${message.role === 'user'
                    ? 'border-lcars-gold bg-lcars-gold/5 text-lcars-gold'
                    : 'border-lcars-lavender bg-lcars-lavender/5 text-lcars-lavender'
                    } relative`}>
                    {/* Corner accent */}
                    <div className={`absolute -top-1 -left-1 w-4 h-4 border-t-2 border-l-2 ${message.role === 'user' ? 'border-lcars-gold' : 'border-lcars-lavender'
                      }`}></div>

                    <div className="text-lg leading-relaxed font-medium tracking-wide">
                      {message.content}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* REGION 4: Bottom Footer (Command Console) */}
          <div className="h-32 mt-2 bg-lcars-gold/10 rounded-[30px] border-2 border-lcars-gold/30 p-4 flex items-center gap-4 relative">
            {/* Decorative Grid Background */}
            <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'linear-gradient(#FFD185 1px, transparent 1px), linear-gradient(90deg, #FFD185 1px, transparent 1px)', backgroundSize: '20px 20px' }}></div>

            {/* Left Aux Controls */}
            <div className="w-48 h-full flex flex-col gap-2 justify-center">
              <div className="flex gap-1">
                <div className="h-6 w-12 bg-lcars-orange rounded-full opacity-60"></div>
                <div className="h-6 w-full bg-lcars-blue rounded-full opacity-40"></div>
              </div>
              <div className="flex gap-1">
                <div className="h-6 w-full bg-lcars-lavender rounded-full opacity-40"></div>
                <div className="h-6 w-12 bg-lcars-gold rounded-full opacity-60"></div>
              </div>
              <div className="h-2 w-full bg-lcars-red/50 rounded-full mt-1"></div>
            </div>

            {/* Main Input */}
            <div className="flex-1 flex gap-4 z-10">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="ENTER COMMAND..."
                className="flex-1 bg-black border-2 border-lcars-orange rounded-full px-8 text-xl text-lcars-orange font-antonio tracking-widest focus:outline-none focus:shadow-[0_0_30px_rgba(255,156,40,0.4)] transition-all placeholder-lcars-orange/30"
                disabled={isLoading}
                autoFocus
              />
              <button
                onClick={sendMessage}
                disabled={isLoading || !input.trim()}
                className="bg-lcars-orange hover:bg-lcars-orange-light text-black font-antonio font-bold text-xl tracking-widest px-12 rounded-full transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:hover:scale-100"
              >
                ENGAGE
              </button>
            </div>

            {/* Right Aux Controls */}
            <div className="w-48 h-full flex flex-col gap-2 justify-center items-end">
              <div className="flex gap-1 w-full justify-end">
                <div className="h-6 w-full bg-lcars-blue rounded-full opacity-40"></div>
                <div className="h-6 w-8 bg-lcars-orange rounded-full opacity-60"></div>
              </div>
              <div className="flex gap-1 w-full justify-end">
                <div className="h-6 w-8 bg-lcars-gold rounded-full opacity-60"></div>
                <div className="h-6 w-full bg-lcars-lavender rounded-full opacity-40"></div>
              </div>
              <div className="flex gap-1 mt-1">
                <div className="w-2 h-2 bg-lcars-red rounded-full animate-pulse"></div>
                <div className="w-2 h-2 bg-lcars-red rounded-full animate-pulse delay-75"></div>
                <div className="w-2 h-2 bg-lcars-red rounded-full animate-pulse delay-150"></div>
              </div>
            </div>

          </div>

        </main>
      </div>
    </div>
  )
}
