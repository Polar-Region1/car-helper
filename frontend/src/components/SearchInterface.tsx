import { useState, useEffect } from 'react'
import { marked } from 'marked'
import { sendChatMessage, getSessionHistory, type Session } from '@/utils/api'
import { cn } from '@/lib/utils'

// 配置marked
marked.setOptions({
  breaks: true,
  gfm: true,
  // @ts-ignore
  headerIds: false,
  mangle: false
})

interface Car {
  name: string
  price: string
  energy: string
  level: string
  badge?: string
}

const quickTags = [
  { id: 1, label: '10-20万 EV', query: '推荐10-20万新能源车' },
  { id: 2, label: 'BYD SUV', query: '比亚迪有哪些SUV' },
  { id: 3, label: 'Pure EV', query: '推荐纯电动轿车' },
  { id: 4, label: 'Hybrid', query: '有哪些混动车型' },
]

export function SearchInterface() {
  const [searchQuery, setSearchQuery] = useState('')
  const [currentQuery, setCurrentQuery] = useState('')
  const [aiAnalysis, setAiAnalysis] = useState('')
  const [thinkingProcess, setThinkingProcess] = useState('')
  const [showThinking, setShowThinking] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [displayCars, setDisplayCars] = useState<Car[]>([])
  const [sessions, setSessions] = useState<Session[]>([])

  const [sessionId] = useState(() => {
    let id = localStorage.getItem('current_session_id')
    if (!id) {
      id = `session_${Date.now()}`
      localStorage.setItem('current_session_id', id)
    }
    return id
  })

  const hasResults = displayCars.length > 0 || aiAnalysis || isLoading

  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    try {
      const data = await getSessionHistory()
      setSessions(data)
    } catch (e) {
      console.error('Failed to load sessions:', e)
    }
  }

  const formatTime = (timeStr: string) => {
    if (!timeStr) return ''
    try {
      const date = new Date(timeStr)
      const now = new Date()
      const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
      if (diff < 60) return 'Just now'
      if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
      if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
      return `${Math.floor(diff / 86400)}d ago`
    } catch (e) {
      return timeStr
    }
  }

  const quickFilter = (query: string) => {
    setSearchQuery(query)
    handleSearch(query)
  }

  const resetSearch = () => {
    setCurrentQuery('')
    setAiAnalysis('')
    setThinkingProcess('')
    setDisplayCars([])
    setShowThinking(false)
    setIsLoading(false)
    setSearchQuery('')
  }

  const handleSearch = async (query?: string) => {
    const q = query || searchQuery
    if (!q.trim() || isLoading) return

    setCurrentQuery(q)
    setIsLoading(true)
    setAiAnalysis('')
    setThinkingProcess('')
    setDisplayCars([])
    setShowThinking(false)

    try {
      await sendChatMessage(q, sessionId, (chunk) => {
        if (chunk.type === 'reasoning_content') {
          setThinkingProcess(prev => prev + chunk.content)
        } else if (chunk.type === 'content') {
          setAiAnalysis(prev => prev + chunk.content)
        } else if (chunk.type === 'cars_data' && chunk.cars) {
          setDisplayCars(chunk.cars)
        }
      })

      await loadSessions()

      // 缓存结果
      const resultCache = {
        query: q,
        analysis: aiAnalysis,
        thinking: thinkingProcess,
        cars: displayCars,
        timestamp: Date.now()
      }
      localStorage.setItem(`session_result_${sessionId}`, JSON.stringify(resultCache))

    } catch (error) {
      console.error('Search failed:', error)
      setAiAnalysis(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsLoading(false)
    }
  }

  const resumeSession = async (sid: string) => {
    const cachedResult = localStorage.getItem(`session_result_${sid}`)

    if (cachedResult) {
      try {
        const cached = JSON.parse(cachedResult)
        localStorage.setItem('current_session_id', sid)

        setCurrentQuery(cached.query)
        setAiAnalysis(cached.analysis)
        setThinkingProcess(cached.thinking || '')
        setDisplayCars(cached.cars || [])
        return
      } catch (e) {
        console.error('Failed to parse cache:', e)
      }
    }

    localStorage.setItem('current_session_id', sid)
    const session = sessions.find(s => s.id === sid)
    if (session && session.last_query) {
      setSearchQuery(session.last_query)
      handleSearch(session.last_query)
    }
  }

  if (hasResults) {
    return (
      <section className="py-16">
        <div className="container mx-auto px-8">
          {/* Back button */}
          <button
            onClick={resetSearch}
            className="px-6 py-3 mb-16 border border-border bg-transparent text-sm text-foreground hover:bg-foreground hover:text-background transition-all"
          >
            ← Back to Search
          </button>

          {/* AI Analysis */}
          {(aiAnalysis || isLoading) && (
            <div className="mb-24 p-12 border border-border">
              <div className="flex justify-between items-center mb-6 pb-6 border-b border-border">
                <h2 className="text-sm font-semibold tracking-widest uppercase">Analysis</h2>
                {thinkingProcess && (
                  <button
                    onClick={() => setShowThinking(!showThinking)}
                    className="px-4 py-2 border border-border bg-transparent text-xs text-foreground hover:bg-muted transition-all"
                  >
                    {showThinking ? 'Hide Process' : 'Show Process'}
                  </button>
                )}
              </div>

              {/* Thinking process */}
              {showThinking && thinkingProcess && (
                <div className="mb-6 p-6 bg-muted">
                  <h3 className="text-xs font-semibold tracking-widest uppercase mb-4 text-muted-foreground">
                    Reasoning
                  </h3>
                  <pre className="font-mono text-xs leading-relaxed text-foreground whitespace-pre-wrap">
                    {thinkingProcess}
                  </pre>
                </div>
              )}

              {/* Analysis content */}
              <div className="text-base leading-relaxed">
                {aiAnalysis && (
                  <div
                    className="prose prose-sm max-w-none"
                    dangerouslySetInnerHTML={{ __html: marked.parse(aiAnalysis) }}
                  />
                )}
                {isLoading && !aiAnalysis && (
                  <div className="py-6">
                    <div className="loading-bar" />
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Cars grid */}
          {displayCars.length > 0 && (
            <div className="mt-24">
              <div className="flex justify-between items-baseline mb-6 pb-6 border-b border-border">
                <h2 className="text-sm font-semibold tracking-widest uppercase">Results</h2>
                <span className="text-sm text-muted-foreground">{displayCars.length} cars</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {displayCars.map((car, index) => (
                  <article key={index} className="border border-border hover:border-foreground transition-colors">
                    {/* Car image */}
                    <div className="relative aspect-video bg-muted flex items-center justify-center border-b border-border">
                      <svg className="w-20 h-20 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                        <path d="M5 17h14M5 17v-4M5 17l-2 2M19 17v-4M19 17l2 2M7 13V7l2-2h6l2 2v6"/>
                        <circle cx="8" cy="17" r="1"/>
                        <circle cx="16" cy="17" r="1"/>
                      </svg>
                      {car.badge && (
                        <span className="absolute top-4 right-4 px-4 py-2 bg-foreground text-background text-xs font-semibold tracking-wider uppercase">
                          {car.badge}
                        </span>
                      )}
                    </div>

                    {/* Car content */}
                    <div className="p-6">
                      <h3 className="text-base font-semibold mb-4">{car.name}</h3>

                      <dl className="grid grid-cols-2 gap-4 mb-6 pb-6 border-b border-border">
                        <div className="flex flex-col gap-2">
                          <dt className="text-xs font-semibold tracking-wider uppercase text-muted-foreground">Energy</dt>
                          <dd className="text-sm">{car.energy}</dd>
                        </div>
                        <div className="flex flex-col gap-2">
                          <dt className="text-xs font-semibold tracking-wider uppercase text-muted-foreground">Type</dt>
                          <dd className="text-sm">{car.level}</dd>
                        </div>
                      </dl>

                      <div className="flex justify-between items-baseline mb-6">
                        <span className="text-xs text-muted-foreground">Price</span>
                        <span className="text-lg font-bold">{car.price}</span>
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <button className="py-3 px-4 bg-foreground text-background text-sm font-medium hover:opacity-80 transition-opacity">
                          Details
                        </button>
                        <button className="py-3 px-4 border border-border bg-transparent text-sm font-medium hover:bg-muted transition-colors">
                          Compare
                        </button>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>
    )
  }

  return (
    <section className="min-h-[calc(100vh-4rem)] flex items-center py-24">
      <div className="container mx-auto px-8">
        <div className="max-w-3xl mx-auto">
          {/* Hero title */}
          <h1 className="text-5xl font-black tracking-tight leading-tight mb-4">
            Find Your Car
          </h1>
          <p className="text-lg text-muted-foreground mb-16">
            AI-powered intelligent search system
          </p>

          {/* Search box */}
          <div className={cn(
            "grid grid-cols-[1fr_auto] gap-0 border-2 border-border mb-8 transition-colors",
            "focus-within:border-foreground"
          )}>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Describe your needs, e.g., 10-20万 new energy SUV"
              disabled={isLoading}
              className="px-8 py-6 bg-transparent border-none outline-none text-base"
            />
            <button
              onClick={() => handleSearch()}
              disabled={isLoading || !searchQuery.trim()}
              className="px-12 py-6 bg-foreground text-background text-sm font-semibold hover:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
            >
              {isLoading ? 'Searching...' : 'Search'}
            </button>
          </div>

          {/* Quick tags */}
          <div className="flex gap-2 flex-wrap mb-24">
            {quickTags.map(tag => (
              <button
                key={tag.id}
                onClick={() => quickFilter(tag.query)}
                disabled={isLoading}
                className="px-4 py-2 border border-border bg-transparent text-sm text-foreground hover:bg-foreground hover:text-background disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                {tag.label}
              </button>
            ))}
          </div>

          {/* History */}
          {sessions.length > 0 && (
            <div className="mt-24 pt-24 border-t border-border">
              <h2 className="text-sm font-semibold tracking-widest uppercase mb-8 text-muted-foreground">
                Recent Searches
              </h2>

              <div className="grid gap-px bg-border border border-border">
                {sessions.slice(0, 6).map((session, idx) => (
                  <button
                    key={session.id}
                    onClick={() => resumeSession(session.id)}
                    className="grid grid-cols-[auto_1fr_auto] gap-4 items-center px-6 py-6 bg-background text-left hover:bg-muted transition-colors"
                  >
                    <span className="text-xs font-semibold text-muted-foreground">
                      {String(idx + 1).padStart(2, '0')}
                    </span>
                    <span className="text-sm text-foreground truncate">
                      {session.last_query || '(Untitled)'}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {formatTime(session.update_time)}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
