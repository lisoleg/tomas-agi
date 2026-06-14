// 错误边界组件 - 捕获渲染错误，避免整个应用黑屏
import React, { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: string
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: '' }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[ErrorBoundary] 捕获到渲染错误:', error, errorInfo)
    this.setState({ errorInfo: errorInfo.componentStack || '' })
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center px-6 py-8 bg-red-900/20 border border-red-500/30 rounded-lg m-4">
          <div className="text-4xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-red-300 mb-2">组件渲染出错</h2>
          <p className="text-sm text-red-200/70 mb-4 max-w-md">
            某个组件在渲染过程中抛出了未捕获的错误。
          </p>
          <div className="bg-black/30 rounded-md p-4 mb-4 max-w-2xl overflow-auto text-left">
            <div className="text-xs text-red-400 font-mono mb-2">
              {this.state.error?.toString()}
            </div>
            <div className="text-xs text-red-300/50 font-mono whitespace-pre-wrap">
              {this.state.errorInfo}
            </div>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-red-600/80 hover:bg-red-500 text-white rounded-md text-sm transition-colors"
          >
            刷新页面
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
