import { useEffect, useRef, useState } from 'react'
import DOMPurify from 'dompurify'
import { marked } from 'marked'

import {
  getSessionHistory,
  getSessionMessages,
  sendChatMessage,
  type Car,
  type Message as StoredMessage,
  type Session
} from '@/utils/api'
import { MemoryPanel } from './MemoryPanel'

marked.setOptions({ breaks: true, gfm: true })

type MessageStatus = 'streaming' | 'complete' | 'error'

interface ConversationMessage {
  id: string
  role: 'user' | 'agent'
  content: string
  reasoning: string
  cars: Car[]
  status: MessageStatus
  error?: string
}

const quickTags = [
  { id: 1, label: '10-20万 EV', query: '推荐10-20万新能源车' },
  { id: 2, label: 'BYD SUV', query: '比亚迪有哪些SUV' },
  { id: 3, label: 'Pure EV', query: '推荐纯电动轿车' },
  { id: 4, label: 'Hybrid', query: '有哪些混动车型' }
]

const STORAGE_PREFIX = 'car_helper_v2'
const CURRENT_SESSION_KEY = `${STORAGE_PREFIX}_current_session_id`

function createId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
}

function createSessionId(): string {
  return createId('session')
}

function cacheKey(sessionId: string): string {
  return `${STORAGE_PREFIX}_session_messages_${sessionId}`
}

function isCar(value: unknown): value is Car {
  if (!value || typeof value !== 'object') return false
  const car = value as Record<string, unknown>
  return ['name', 'price', 'energy', 'level'].every(field => typeof car[field] === 'string')
}

function readCachedMessages(sessionId: string): ConversationMessage[] | null {
  try {
    const raw = localStorage.getItem(cacheKey(sessionId))
    if (!raw) return null
    const parsed = JSON.parse(raw) as { messages?: unknown }
    if (!Array.isArray(parsed.messages)) return null

    const messages: ConversationMessage[] = []
    for (const item of parsed.messages) {
      if (!item || typeof item !== 'object') return null
      const value = item as Record<string, unknown>
      if (
        typeof value.id !== 'string' ||
        (value.role !== 'user' && value.role !== 'agent') ||
        typeof value.content !== 'string'
      ) {
        return null
      }
      messages.push({
        id: value.id,
        role: value.role,
        content: value.content,
        reasoning: typeof value.reasoning === 'string' ? value.reasoning : '',
        cars: Array.isArray(value.cars) ? value.cars.filter(isCar) : [],
        status:
          value.status === 'streaming' || value.status === 'error'
            ? value.status
            : 'complete',
        error: typeof value.error === 'string' ? value.error : undefined
      })
    }
    return messages
  } catch {
    return null
  }
}

function writeCachedMessages(sessionId: string, messages: ConversationMessage[]): void {
  try {
    localStorage.setItem(cacheKey(sessionId), JSON.stringify({ messages, timestamp: Date.now() }))
  } catch (error) {
    console.error('Failed to cache conversation:', error)
  }
}

function restoreStoredMessages(sessionId: string, messages: StoredMessage[]): ConversationMessage[] {
  return messages.map((message, index) => ({
    id: `${sessionId}_${index}`,
    role: message.role,
    content: message.content,
    reasoning: '',
    cars: [],
    status: 'complete'
  }))
}

function enrichStoredMessages(
  stored: ConversationMessage[],
  cached: ConversationMessage[] | null
): ConversationMessage[] {
  if (!cached) return stored
  return stored.map((message, index) => {
    const cachedMessage = cached[index]
    if (
      !cachedMessage ||
      cachedMessage.role !== message.role ||
      cachedMessage.content !== message.content
    ) {
      return message
    }
    return {
      ...message,
      reasoning: cachedMessage.reasoning,
      cars: cachedMessage.cars,
      status: cachedMessage.status,
      error: cachedMessage.error
    }
  })
}

function mergeCars(current: Car[], incoming: Car[]): Car[] {
  return Array.from(
    new Map(
      [...current, ...incoming].map(car => [
        `${car.name}\u0000${car.price}\u0000${car.energy}\u0000${car.level}`,
        car
      ])
    ).values()
  )
}

function formatTime(time: string): string {
  if (!time) return ''
  const date = new Date(time)
  if (Number.isNaN(date.getTime())) return time
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000))
  if (seconds < 60) return 'Just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
}

function CarGrid({ cars }: { cars: Car[] }) {
  if (cars.length === 0) return null
  return (
    <div className="mt-8">
      <div className="flex justify-between items-baseline mb-4 pb-4 border-b border-border">
        <h3 className="text-xs font-semibold tracking-widest uppercase">Results</h3>
        <span className="text-xs text-muted-foreground">{cars.length} cars</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {cars.map((car, index) => (
          <article
            key={`${car.name}_${car.price}_${index}`}
            className="border border-border hover:border-foreground transition-colors"
          >
            <div className="relative aspect-video bg-muted flex items-center justify-center border-b border-border">
              <svg
                className="w-16 h-16 text-muted-foreground"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1"
                aria-hidden="true"
              >
                <path d="M5 17h14M5 17v-4M5 17l-2 2M19 17v-4M19 17l2 2M7 13V7l2-2h6l2 2v6" />
                <circle cx="8" cy="17" r="1" />
                <circle cx="16" cy="17" r="1" />
              </svg>
              {car.badge && (
                <span className="absolute top-3 right-3 px-3 py-1.5 bg-foreground text-background text-xs font-semibold tracking-wider uppercase">
                  {car.badge}
                </span>
              )}
            </div>
            <div className="p-5">
              <h4 className="text-sm font-semibold mb-4">{car.name}</h4>
              <dl className="grid grid-cols-2 gap-4 mb-4 pb-4 border-b border-border">
                <div>
                  <dt className="text-xs uppercase text-muted-foreground mb-1">Energy</dt>
                  <dd className="text-sm">{car.energy}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase text-muted-foreground mb-1">Type</dt>
                  <dd className="text-sm">{car.level}</dd>
                </div>
              </dl>
              <div className="flex justify-between items-baseline">
                <span className="text-xs text-muted-foreground">Price</span>
                <span className="text-base font-bold">{car.price}</span>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}

interface ComposerProps {
  query: string
  loading: boolean
  onQueryChange: (query: string) => void
  onSubmit: () => void
}

function Composer({ query, loading, onQueryChange, onSubmit }: ComposerProps) {
  return (
    <form
      className="grid grid-cols-[1fr_auto] border-2 border-border transition-colors focus-within:border-foreground"
      onSubmit={event => {
        event.preventDefault()
        onSubmit()
      }}
    >
      <input
        type="text"
        value={query}
        onChange={event => onQueryChange(event.target.value)}
        placeholder="继续提问，例如：这几款车哪款更适合家用？"
        disabled={loading}
        className="min-w-0 px-6 py-5 bg-background border-none outline-none text-base"
      />
      <button
        type="submit"
        disabled={loading || !query.trim()}
        className="px-8 py-5 bg-foreground text-background text-sm font-semibold hover:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
      >
        {loading ? '回答中...' : '发送'}
      </button>
    </form>
  )
}

export function SearchInterface() {
  const [sessionId, setSessionId] = useState(() => {
    const stored = localStorage.getItem(CURRENT_SESSION_KEY)
    if (stored) return stored
    const created = createSessionId()
    localStorage.setItem(CURRENT_SESSION_KEY, created)
    return created
  })
  const [messages, setMessages] = useState<ConversationMessage[]>(
    () => readCachedMessages(sessionId) ?? []
  )
  const [searchQuery, setSearchQuery] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [isHistoryLoading, setIsHistoryLoading] = useState(false)
  const [sessions, setSessions] = useState<Session[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [expandedReasoning, setExpandedReasoning] = useState<Set<string>>(new Set())
  const historyRef = useRef<HTMLDivElement>(null)

  const hasConversation = messages.length > 0

  useEffect(() => {
    void getSessionHistory()
      .then(setSessions)
      .catch(error => console.error('Failed to load sessions:', error))

    const handleClickOutside = (event: MouseEvent) => {
      if (historyRef.current && !historyRef.current.contains(event.target as Node)) {
        setShowHistory(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const refreshSessions = async () => {
    try {
      setSessions(await getSessionHistory())
    } catch (error) {
      console.error('Failed to load sessions:', error)
    }
  }

  const updateMessage = (messageId: string, update: Partial<ConversationMessage>) => {
    setMessages(current =>
      current.map(message => (message.id === messageId ? { ...message, ...update } : message))
    )
  }

  const handleSearch = async (query = searchQuery) => {
    const question = query.trim()
    if (!question || isStreaming || isHistoryLoading) return

    const userMessage: ConversationMessage = {
      id: createId('user'),
      role: 'user',
      content: question,
      reasoning: '',
      cars: [],
      status: 'complete'
    }
    const agentMessage: ConversationMessage = {
      id: createId('agent'),
      role: 'agent',
      content: '',
      reasoning: '',
      cars: [],
      status: 'streaming'
    }
    const conversation = [...messages, userMessage, agentMessage]
    let activeSessionId = sessionId
    let content = ''
    let reasoning = ''
    let cars: Car[] = []

    setMessages(conversation)
    setSearchQuery('')
    setIsStreaming(true)

    try {
      await sendChatMessage(question, sessionId, chunk => {
        if (chunk.type === 'connected') {
          activeSessionId = chunk.session_id
          if (chunk.session_id !== sessionId) {
            setSessionId(chunk.session_id)
            localStorage.setItem(CURRENT_SESSION_KEY, chunk.session_id)
          }
        } else if (chunk.type === 'reasoning_content') {
          reasoning += chunk.content
          updateMessage(agentMessage.id, { reasoning })
        } else if (chunk.type === 'content') {
          content += chunk.content
          updateMessage(agentMessage.id, { content })
        } else if (chunk.type === 'cars_data') {
          cars = mergeCars(cars, chunk.cars)
          updateMessage(agentMessage.id, { cars })
        } else if (chunk.type === 'done') {
          updateMessage(agentMessage.id, { status: 'complete' })
        }
      })

      const completed = conversation.map(message =>
        message.id === agentMessage.id
          ? { ...message, content, reasoning, cars, status: 'complete' as const }
          : message
      )
      setMessages(completed)
      writeCachedMessages(activeSessionId, completed)
      await refreshSessions()
    } catch (error) {
      const errorText = error instanceof Error ? error.message : '未知错误'
      const failed = conversation.map(message =>
        message.id === agentMessage.id
          ? { ...message, content, reasoning, cars, status: 'error' as const, error: errorText }
          : message
      )
      setMessages(failed)
      writeCachedMessages(activeSessionId, failed)
    } finally {
      setIsStreaming(false)
    }
  }

  const resumeSession = async (selectedSessionId: string) => {
    if (isStreaming || isHistoryLoading) return
    setShowHistory(false)
    setIsHistoryLoading(true)
    setSearchQuery('')
    setExpandedReasoning(new Set())
    setSessionId(selectedSessionId)
    localStorage.setItem(CURRENT_SESSION_KEY, selectedSessionId)

    const cached = readCachedMessages(selectedSessionId)
    setMessages(cached ?? [])
    try {
      const stored = await getSessionMessages(selectedSessionId)
      const restored = enrichStoredMessages(
        restoreStoredMessages(selectedSessionId, stored),
        cached
      )
      setMessages(restored)
      writeCachedMessages(selectedSessionId, restored)
    } catch (error) {
      console.error('Failed to load session messages:', error)
      if (!cached) {
        setMessages([
          {
            id: createId('history_error'),
            role: 'agent',
            content: '',
            reasoning: '',
            cars: [],
            status: 'error',
            error: '历史对话加载失败，请稍后重试。'
          }
        ])
      }
    } finally {
      setIsHistoryLoading(false)
    }
  }

  const startNewConversation = () => {
    if (isStreaming) return
    const newSessionId = createSessionId()
    localStorage.setItem(CURRENT_SESSION_KEY, newSessionId)
    setSessionId(newSessionId)
    setMessages([])
    setSearchQuery('')
    setExpandedReasoning(new Set())
    setShowHistory(false)
  }

  const toggleReasoning = (messageId: string) => {
    setExpandedReasoning(current => {
      const next = new Set(current)
      if (next.has(messageId)) next.delete(messageId)
      else next.add(messageId)
      return next
    })
  }

  const historyMenu = (
    <div className="relative" ref={historyRef}>
      <button
        type="button"
        onClick={() => setShowHistory(current => !current)}
        disabled={isStreaming || isHistoryLoading}
        aria-expanded={showHistory}
        className="px-5 py-3 border border-border bg-background text-sm hover:bg-foreground hover:text-background disabled:opacity-50 transition-all flex items-center gap-2"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        {isHistoryLoading ? 'Loading...' : `History (${sessions.length})`}
      </button>
      {showHistory && (
        <div className="absolute right-0 top-full mt-2 w-[min(24rem,calc(100vw-4rem))] border border-border bg-background shadow-lg z-50">
          <div className="max-h-96 overflow-y-auto">
            {sessions.length === 0 ? (
              <p className="px-4 py-6 text-sm text-muted-foreground">暂无历史会话</p>
            ) : (
              sessions.map((session, index) => (
                <button
                  type="button"
                  key={session.id}
                  onClick={() => void resumeSession(session.id)}
                  className="w-full grid grid-cols-[auto_1fr_auto] gap-4 items-center px-4 py-4 text-left hover:bg-muted transition-colors border-b border-border last:border-b-0"
                >
                  <span className="text-xs font-semibold text-muted-foreground">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <span className="text-sm truncate">
                    {session.title || session.last_query || '(Untitled)'}
                  </span>
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {formatTime(session.update_time)}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )

  return (
    <section className={hasConversation ? 'py-12' : 'min-h-[calc(100vh-4rem)] flex items-center py-24'}>
      <div className="container mx-auto px-8">
        <div className={hasConversation ? 'max-w-5xl mx-auto' : 'max-w-3xl mx-auto'}>
          <div className="flex justify-between items-start gap-6 mb-8">
            {hasConversation ? (
              <button
                type="button"
                onClick={startNewConversation}
                disabled={isStreaming}
                className="px-5 py-3 border border-border bg-background text-sm hover:bg-foreground hover:text-background disabled:opacity-50 transition-all"
              >
                + New conversation
              </button>
            ) : (
              <div>
                <h1 className="text-5xl font-black tracking-tight leading-tight mb-4">Find Your Car</h1>
                <p className="text-lg text-muted-foreground">AI-powered intelligent search system</p>
              </div>
            )}
            <div className="flex items-center gap-2">
              <MemoryPanel />
              {historyMenu}
            </div>
          </div>

          {hasConversation ? (
            <>
              <div className="space-y-8 mb-10" aria-live="polite">
                {messages.map(message =>
                  message.role === 'user' ? (
                    <div key={message.id} className="flex justify-end">
                      <div className="max-w-2xl bg-foreground text-background px-6 py-4">
                        <p className="whitespace-pre-wrap">{message.content}</p>
                      </div>
                    </div>
                  ) : (
                    <article key={message.id} className="border border-border p-8">
                      <div className="flex justify-between items-center mb-5 pb-5 border-b border-border">
                        <h2 className="text-xs font-semibold tracking-widest uppercase">Agent</h2>
                        {message.reasoning && (
                          <button
                            type="button"
                            onClick={() => toggleReasoning(message.id)}
                            className="px-3 py-2 border border-border text-xs hover:bg-muted transition-colors"
                          >
                            {expandedReasoning.has(message.id) ? 'Hide Process' : 'Show Process'}
                          </button>
                        )}
                      </div>
                      {expandedReasoning.has(message.id) && message.reasoning && (
                        <div className="mb-6 p-5 bg-muted">
                          <h3 className="text-xs font-semibold tracking-widest uppercase mb-3 text-muted-foreground">
                            Reasoning
                          </h3>
                          <pre className="font-mono text-xs leading-relaxed whitespace-pre-wrap">
                            {message.reasoning}
                          </pre>
                        </div>
                      )}
                      {message.content && (
                        <div
                          className="prose prose-sm max-w-none"
                          dangerouslySetInnerHTML={{
                            __html: DOMPurify.sanitize(marked.parse(message.content) as string)
                          }}
                        />
                      )}
                      {message.status === 'streaming' && !message.content && (
                        <div className="py-5 overflow-hidden"><div className="loading-bar" /></div>
                      )}
                      {message.status === 'error' && (
                        <p className="mt-4 text-sm text-red-600">Error: {message.error}</p>
                      )}
                      {(message.content || message.status !== 'streaming') && (
                        <CarGrid cars={message.cars} />
                      )}
                    </article>
                  )
                )}
              </div>
              <div className="sticky bottom-0 bg-background py-4 border-t border-border">
                <Composer
                  query={searchQuery}
                  loading={isStreaming}
                  onQueryChange={setSearchQuery}
                  onSubmit={() => void handleSearch()}
                />
              </div>
            </>
          ) : (
            <>
              <Composer
                query={searchQuery}
                loading={isStreaming}
                onQueryChange={setSearchQuery}
                onSubmit={() => void handleSearch()}
              />
              <div className="flex gap-2 flex-wrap mt-8">
                {quickTags.map(tag => (
                  <button
                    type="button"
                    key={tag.id}
                    onClick={() => void handleSearch(tag.query)}
                    disabled={isStreaming}
                    className="px-4 py-2 border border-border bg-transparent text-sm hover:bg-foreground hover:text-background disabled:opacity-30 transition-all"
                  >
                    {tag.label}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  )
}
