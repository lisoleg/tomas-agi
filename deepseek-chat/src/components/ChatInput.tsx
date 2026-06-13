// 输入框：支持 Enter 发送 / Shift+Enter 换行、可自动生长、显示发送与停止按钮
import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { IconSend, IconStop } from './icons'

interface ChatInputProps {
  /** 禁用输入（API Key 未配置时） */
  disabled?: boolean
  /** 是否正在流式接收 */
  isLoading: boolean
  /** 占位文字 */
  placeholder?: string
  /** 发送消息 */
  onSend: (text: string) => void
  /** 中止当前请求 */
  onAbort: () => void
}

const MAX_HEIGHT = 200

export function ChatInput(props: ChatInputProps) {
  const { disabled, isLoading, placeholder, onSend, onAbort } = props
  const [value, setValue] = useState('')
  const taRef = useRef<HTMLTextAreaElement>(null)

  // 自动调整高度
  const adjustHeight = () => {
    const ta = taRef.current
    if (!ta) return
    ta.style.height = 'auto'
    const next = Math.min(ta.scrollHeight, MAX_HEIGHT)
    ta.style.height = `${next}px`
  }

  useEffect(() => {
    adjustHeight()
  }, [value])

  /** 发送 */
  const handleSend = () => {
    const text = value.trim()
    if (!text || disabled || isLoading) return
    onSend(text)
    setValue('')
    // 清空后恢复高度
    requestAnimationFrame(() => {
      const ta = taRef.current
      if (ta) ta.style.height = 'auto'
    })
  }

  /** 键盘事件 */
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="w-full max-w-3xl mx-auto px-3 pb-4 pt-2">
      <div
        className={[
          'flex items-end gap-2',
          'rounded-2xl border border-white/15',
          'bg-inputBg shadow-lg',
          'pl-3 pr-2 py-2',
          disabled ? 'opacity-60' : ''
        ].join(' ')}
      >
        <textarea
          ref={taRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          placeholder={placeholder || '发消息给 DeepSeek…（Enter 发送，Shift+Enter 换行）'}
          className={[
            'flex-1 resize-none bg-transparent outline-none',
            'text-[15px] leading-6 text-textPrimary placeholder:text-textSecondary',
            'max-h-[200px] min-h-[28px] py-1.5',
            'disabled:cursor-not-allowed'
          ].join(' ')}
        />

        {isLoading ? (
          <button
            onClick={onAbort}
            className="flex-shrink-0 w-9 h-9 rounded-md bg-white text-chatBg flex items-center justify-center hover:bg-gray-200 transition-colors"
            title="停止生成"
            aria-label="停止生成"
          >
            <IconStop size={16} />
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={disabled || value.trim() === ''}
            className={[
              'flex-shrink-0 w-9 h-9 rounded-md flex items-center justify-center transition-colors',
              value.trim() === '' || disabled
                ? 'bg-white/10 text-textSecondary cursor-not-allowed'
                : 'bg-white text-chatBg hover:bg-gray-200'
            ].join(' ')}
            title="发送"
            aria-label="发送"
          >
            <IconSend size={16} />
          </button>
        )}
      </div>
      <div className="mt-2 text-center text-[11px] text-textSecondary">
        内容由 AI 生成，仅供参考
      </div>
    </div>
  )
}
