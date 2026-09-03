/**
 * API通信工具 - SSE流式通信
 */

export interface ChatChunk {
  type: 'reasoning_content' | 'content' | 'cars_data' | 'tool_start' | 'tool_end'
  content?: string
  cars?: Array<{
    name: string
    price: string
    energy: string
    level: string
    badge?: string
  }>
  tool_name?: string
  result?: string
}

export async function sendChatMessage(
  message: string,
  sessionId: string,
  onChunk: (chunk: ChatChunk) => void
): Promise<void> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: message,
      session_id: sessionId
    })
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('No reader available')

  const decoder = new TextDecoder()
  let buffer = ''
  let currentEvent = 'message'

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim()
        continue
      }

      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim()
        if (data === '[DONE]') continue

        try {
          const parsed = JSON.parse(data)

          if (currentEvent === 'reasoning' && parsed.text) {
            onChunk({ type: 'reasoning_content', content: parsed.text })
          } else if (currentEvent === 'content' && parsed.text) {
            onChunk({ type: 'content', content: parsed.text })
          } else if (currentEvent === 'cars_data' && parsed.cars) {
            onChunk({ type: 'cars_data', cars: parsed.cars })
          } else if (currentEvent === 'tool_start' && parsed.tool_name) {
            onChunk({ type: 'tool_start', tool_name: parsed.tool_name })
          } else if (currentEvent === 'tool_end' && parsed.tool_name) {
            onChunk({ type: 'tool_end', tool_name: parsed.tool_name, result: parsed.result })
          }
        } catch (e) {
          console.warn('Failed to parse SSE data:', data, e)
        }
      }
    }
  }
}

export interface Session {
  id: string
  last_query: string
  create_time: string
  update_time: string
}

export async function getSessionHistory(): Promise<Session[]> {
  const response = await fetch('/api/sessions')
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  const data = await response.json()
  return data.sessions || []
}
