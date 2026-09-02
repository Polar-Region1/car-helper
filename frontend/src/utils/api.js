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
  let buffer = ''
  let currentEvent = 'message'

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || '' // 保留不完整的行

    for (const line of lines) {
      // 解析事件类型
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim()
        continue
      }

      // 解析数据
      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim()

        if (data === '[DONE]') {
          continue
        }

        try {
          const parsed = JSON.parse(data)

          // 根据事件类型处理数据
          if (currentEvent === 'reasoning' && parsed.text) {
            onChunk({
              type: 'reasoning_content',
              content: parsed.text
            })
          }
          else if (currentEvent === 'content' && parsed.text) {
            onChunk({
              type: 'content',
              content: parsed.text
            })
          }
          else if (currentEvent === 'cars_data' && parsed.cars) {
            onChunk({
              type: 'cars_data',
              cars: parsed.cars
            })
          }
          else if (currentEvent === 'tool_start' && parsed.tool_name) {
            onChunk({
              type: 'tool_start',
              tool_name: parsed.tool_name
            })
          }
          else if (currentEvent === 'tool_end' && parsed.tool_name) {
            onChunk({
              type: 'tool_end',
              tool_name: parsed.tool_name,
              result: parsed.result
            })
          }
          else if (currentEvent === 'error' && parsed.message) {
            throw new Error(parsed.message)
          }
        } catch (e) {
          if (e.message && e.message.startsWith('服务')) {
            throw e
          }
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
