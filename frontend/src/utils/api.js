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

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || '' // 保留不完整的行

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        const eventType = line.slice(7).trim()
        continue
      }

      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim()

        if (data === '[DONE]') {
          continue
        }

        try {
          const parsed = JSON.parse(data)

          // 处理推理内容
          if (parsed.text && line.includes('reasoning')) {
            onChunk({
              type: 'reasoning_content',
              content: parsed.text
            })
          }
          // 处理普通内容
          else if (parsed.text) {
            onChunk({
              type: 'content',
              content: parsed.text
            })
          }
          // 处理结构化车型数据
          else if (parsed.cars) {
            onChunk({
              type: 'cars_data',
              cars: parsed.cars
            })
          }
          // 处理工具调用
          else if (parsed.tool_name) {
            onChunk({
              type: 'tool',
              tool_name: parsed.tool_name,
              result: parsed.result
            })
          }
          // 处理错误
          else if (parsed.error) {
            throw new Error(parsed.error)
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
