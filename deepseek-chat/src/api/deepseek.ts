// DeepSeek API 调用层：基于 fetch + ReadableStream 实现 SSE 流式响应
import type { DeepSeekRequestMessage, MessageRole } from '../types'

/** DeepSeek API 配置 */
const DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'
const DEFAULT_MODEL = 'deepseek-chat'
const DEFAULT_TEMPERATURE = 0.7
const DEFAULT_MAX_TOKENS = 4096

/** 流式请求选项 */
export interface StreamChatOptions {
  apiKey: string
  messages: Array<{ role: MessageRole; content: string }>
  model?: string
  temperature?: number
  maxTokens?: number
  /** 每次接收到新 chunk 时的回调 */
  onDelta: (deltaText: string) => void
  /** 正常结束回调 */
  onComplete: () => void
  /** 出错回调 */
  onError: (err: Error) => void
  /** 外部中止信号（可选） */
  signal?: AbortSignal
}

/**
 * 调用 DeepSeek chat completions 接口并以流式方式消费响应。
 * 使用 fetch + ReadableStream 解析 SSE 数据。
 */
export async function streamChatCompletion(options: StreamChatOptions): Promise<void> {
  const {
    apiKey,
    messages,
    model = DEFAULT_MODEL,
    temperature = DEFAULT_TEMPERATURE,
    maxTokens = DEFAULT_MAX_TOKENS,
    onDelta,
    onComplete,
    onError,
    signal
  } = options

  // 参数校验
  if (!apiKey || apiKey.trim() === '') {
    onError(new Error('API Key 为空，请先在左侧栏的 API Key 设置中填写'))
    return
  }
  if (!messages || messages.length === 0) {
    onError(new Error('消息列表为空'))
    return
  }

  // 构造请求体
  const body = {
    model,
    messages: messages.map<DeepSeekRequestMessage>((m) => ({ role: m.role, content: m.content })),
    stream: true,
    temperature,
    max_tokens: maxTokens
  }

  let response: Response
  try {
    response = await fetch(DEEPSEEK_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
        Accept: 'text/event-stream'
      },
      body: JSON.stringify(body),
      signal
    })
  } catch (err) {
    const error = err instanceof Error ? err : new Error('网络请求失败')
    // 用户主动中止视为正常流程
    if (error.name === 'AbortError') {
      onComplete()
      return
    }
    onError(error)
    return
  }

  if (!response.ok) {
    // 尝试解析错误信息
    let errorText = `请求失败：HTTP ${response.status}`
    try {
      const data = await response.json()
      if (data?.error?.message) {
        errorText = `请求失败：${data.error.message}`
      } else if (data?.message) {
        errorText = `请求失败：${data.message}`
      }
    } catch {
      // 忽略 JSON 解析失败，使用默认错误文本
    }
    onError(new Error(errorText))
    return
  }

  if (!response.body) {
    onError(new Error('响应为空，无法进行流式读取'))
    return
  }

  // 解析 ReadableStream
  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  // 累积未完成的一行（跨 chunk 的数据）
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      // 解码本 chunk
      buffer += decoder.decode(value, { stream: true })

      // 按双换行分割 SSE 事件
      const events = buffer.split('\n\n')
      // 最后一个元素可能是不完整的，保留到下次循环
      buffer = events.pop() ?? ''

      for (const event of events) {
        // 逐行处理
        const lines = event.split('\n')
        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data:')) continue
          const payload = trimmed.slice(5).trim()
          if (!payload) continue
          // 流结束标记
          if (payload === '[DONE]') {
            onComplete()
            return
          }
          try {
            const json = JSON.parse(payload) as {
              choices?: Array<{ delta?: { content?: string }; finish_reason?: string | null }>
            }
            const deltaContent = json.choices?.[0]?.delta?.content
            if (deltaContent) {
              onDelta(deltaContent)
            }
            // 收到 finish_reason === 'stop' 也会通过 [DONE] 结束
          } catch {
            // 忽略无法解析的行（可能是心跳或注释）
          }
        }
      }
    }

    // 正常结束（没有显式 [DONE] 时也调用完成回调）
    onComplete()
  } catch (err) {
    const error = err instanceof Error ? err : new Error('流式读取出错')
    if (error.name === 'AbortError') {
      onComplete()
      return
    }
    onError(error)
  } finally {
    try {
      reader.releaseLock()
    } catch {
      // 忽略释放失败
    }
  }
}
