/**
 * 统一 API 客户端
 * ==================
 * 
 * 所有前端 API 调用都通过此客户端，获得：
 * - 一致的错误处理
 * - 自动重试（可选）
 * - 加载状态管理
 * - 用户友好的错误提示
 */

const API_BASE = 'http://localhost:5000/api'

// 错误类型
export class ApiError extends Error {
  status: number
  data: any

  constructor(message: string, status: number, data?: any) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

// 重试配置
const DEFAULT_RETRY = 3
const RETRY_DELAY = 1000 // 1秒

/**
 * 通用 API 请求函数
 * 
 * @param endpoint - API 端点（如 '/corpus'）
 * @param options - fetch 选项
 * @param retry - 重试次数
 */
async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit,
  retry: number = DEFAULT_RETRY
): Promise<T> {
  const url = `${API_BASE}${endpoint}`

  let lastError: Error | null = null

  for (let attempt = 0; attempt <= retry; attempt++) {
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      })

      // 检查 HTTP 状态
      if (!response.ok) {
        const errorText = await response.text()
        let errorMessage = `请求失败 (${response.status})`
        
        try {
          const errorData = JSON.parse(errorText)
          errorMessage = errorData.message || errorData.error || errorMessage
        } catch {
          // 如果不是 JSON，使用原始文本
          if (errorText) errorMessage = errorText
        }

        throw new ApiError(errorMessage, response.status, errorText)
      }

      // 解析 JSON
      const data = await response.json()

      // 检查业务成功标志
      if (data.success === false) {
        throw new ApiError(data.message || '操作失败', 400, data)
      }

      return data as T
    } catch (error) {
      lastError = error as Error

      // 如果是最后一次重试，或者是不应该重试的错误，直接抛出
      if (
        attempt === retry ||
        (error instanceof ApiError && error.status === 400) // 业务错误不重试
      ) {
        break
      }

      // 等待后重试
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * (attempt + 1)))
    }
  }

  throw lastError || new Error('未知错误')
}

/**
 * GET 请求
 */
export async function apiGet<T>(endpoint: string): Promise<T> {
  return apiRequest<T>(endpoint, { method: 'GET' })
}

/**
 * POST 请求
 */
export async function apiPost<T>(endpoint: string, data: any): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/**
 * DELETE 请求
 */
export async function apiDelete<T>(endpoint: string): Promise<T> {
  return apiRequest<T>(endpoint, { method: 'DELETE' })
}

/**
 * PUT 请求
 */
export async function apiPut<T>(endpoint: string, data: any): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

/**
 * 错误处理工具函数
 * 
 * 将 API 错误转换为用户友好的消息
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    // 根据状态码返回友好消息
    switch (error.status) {
      case 404:
        return '请求的资源不存在'
      case 401:
        return '未授权，请检查 API Key'
      case 403:
        return '无权访问此资源'
      case 500:
        return '服务器内部错误，请稍后重试'
      default:
        return error.message || '未知错误'
    }
  }

  if (error instanceof TypeError && error.message.includes('fetch')) {
    return '无法连接到服务器，请检查网络或后端是否启动'
  }

  return String(error)
}

/**
 * 带加载状态的 API 调用包装器
 * 
 * @param apiCall - API 调用函数
 * @param setLoading - 设置加载状态的函数
 * @param setError - 设置错误的函数
 */
export async function withLoading<T>(
  apiCall: () => Promise<T>,
  setLoading?: (loading: boolean) => void,
  setError?: (error: string | null) => void
): Promise<T | null> {
  setLoading?.(true)
  setError?.(null)

  try {
    const result = await apiCall()
    return result
  } catch (error) {
    const message = getErrorMessage(error)
    setError?.(message)
    console.error('API 调用失败:', error)
    return null
  } finally {
    setLoading?.(false)
  }
}
