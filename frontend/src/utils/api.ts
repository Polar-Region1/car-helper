export interface Car {
  name: string
  price: string
  energy: string
  level: string
  badge?: string | null
}

export type ChatChunk =
  | { type: 'connected'; session_id: string }
  | { type: 'reasoning_content'; content: string }
  | { type: 'content'; content: string }
  | { type: 'cars_data'; cars: Car[] }
  | { type: 'tool_start'; tool_name: string }
  | { type: 'tool_end'; tool_name: string; result_count: number }
  | { type: 'done'; elapsed_ms: number }

interface SsePayload {
  session_id?: string
  text?: string
  cars?: Car[]
  tool_name?: string
  result_count?: number
  elapsed_ms?: number
  message?: string
}

function parseEvent(raw: string): { event: string; payload: SsePayload } | null {
  let event = 'message'
  const dataLines: string[] = []
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
  }
  if (dataLines.length === 0) return null
  return { event, payload: JSON.parse(dataLines.join('\n')) as SsePayload }
}

export async function sendChatMessage(
  message: string,
  sessionId: string,
  onChunk: (chunk: ChatChunk) => void
): Promise<void> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId })
  })
  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    throw new Error(detail?.detail || `HTTP ${response.status}`)
  }
  if (!response.body) throw new Error('服务器未返回响应流')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let streamError = ''

  const consume = (raw: string) => {
    const parsed = parseEvent(raw)
    if (!parsed) return
    const { event, payload } = parsed
    if (event === 'connected' && payload.session_id) {
      onChunk({ type: 'connected', session_id: payload.session_id })
    } else if (event === 'reasoning' && payload.text) {
      onChunk({ type: 'reasoning_content', content: payload.text })
    } else if (event === 'content' && payload.text) {
      onChunk({ type: 'content', content: payload.text })
    } else if (event === 'cars_data' && payload.cars) {
      onChunk({ type: 'cars_data', cars: payload.cars })
    } else if (event === 'tool_start' && payload.tool_name) {
      onChunk({ type: 'tool_start', tool_name: payload.tool_name })
    } else if (event === 'tool_end' && payload.tool_name) {
      onChunk({
        type: 'tool_end',
        tool_name: payload.tool_name,
        result_count: payload.result_count || 0
      })
    } else if (event === 'done') {
      onChunk({ type: 'done', elapsed_ms: payload.elapsed_ms || 0 })
    } else if (event === 'error') {
      streamError = payload.message || '服务暂时不可用'
    }
  }

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''
    events.forEach(consume)
  }
  buffer += decoder.decode().replace(/\r\n/g, '\n')
  if (buffer.trim()) consume(buffer)
  if (streamError) throw new Error(streamError)
}

export interface Session {
  id: string
  title: string
  last_query: string
  create_time: string
  update_time: string
}

export interface Message {
  role: 'user' | 'agent'
  content: string
}

export interface Profile {
  profile_id: string
  display_name: string
  created_at: string
  updated_at: string
}

export interface LongTermMemory {
  memory_id: string
  category: string
  key: string
  value: string
  confidence: number
  source_type: 'explicit' | 'confirmed'
  source_thread_id?: string | null
  expires_at?: string | null
  created_at: string
  updated_at: string
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json() as Promise<T>
}

export async function getSessionHistory(): Promise<Session[]> {
  const data = await getJson<{ sessions?: Session[] }>('/api/sessions')
  return data.sessions || []
}

export async function getSessionMessages(sessionId: string): Promise<Message[]> {
  const data = await getJson<{ messages?: Message[] }>(
    `/api/sessions/${encodeURIComponent(sessionId)}/messages`
  )
  return data.messages || []
}

export async function getProfile(): Promise<Profile> {
  return getJson<Profile>('/api/profile')
}

export async function getMemories(): Promise<LongTermMemory[]> {
  const data = await getJson<{ memories?: LongTermMemory[] }>('/api/memories')
  return data.memories || []
}

export async function updateMemory(memoryId: string, value: string): Promise<LongTermMemory> {
  const response = await fetch(`/api/memories/${encodeURIComponent(memoryId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value })
  })
  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    throw new Error(detail?.detail || `HTTP ${response.status}`)
  }
  return response.json() as Promise<LongTermMemory>
}

export async function deleteMemory(memoryId: string): Promise<void> {
  const response = await fetch(`/api/memories/${encodeURIComponent(memoryId)}`, {
    method: 'DELETE'
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
}
