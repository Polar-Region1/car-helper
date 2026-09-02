/**
 * API通信工具
 * 处理与FastAPI后端的SSE流式通信
 */

/**
 * 发送聊天消息并处理流式响应
 * @param {string} message - 用户消息
 * @param {string} sessionId - 会话ID
 * @param {function} onChunk - 接收到数据块时的回调函数
 */
export async function sendChatMessage(message, sessionId, onChunk) {
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

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const chunk = decoder.decode(value)
    const lines = chunk.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim()

        if (data === '[DONE]') {
          continue
        }

        try {
          const parsed = JSON.parse(data)

          // 处理不同类型的事件
          if (parsed.event === 'reasoning_content') {
            onChunk({
              type: 'reasoning_content',
              content: parsed.data
            })
          } else if (parsed.event === 'content') {
            onChunk({
              type: 'content',
              content: parsed.data
            })
          } else if (parsed.event === 'error') {
            throw new Error(parsed.data)
          }
        } catch (e) {
          console.warn('Failed to parse SSE data:', data, e)
        }
      }
    }
  }
}

/**
 * 获取会话历史
 * @param {string} sessionId - 会话ID
 */
export async function getSessionHistory(sessionId) {
  const response = await fetch(`/api/session/${sessionId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    }
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  return await response.json()
}
