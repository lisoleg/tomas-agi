/** Tailwind CSS 配置：自定义 ChatGPT 风格暗色配色 */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // ChatGPT 经典暗色配色
        sidebar: '#202123',
        sidebarHover: '#2A2B32',
        sidebarActive: '#343541',
        chatBg: '#343541',
        chatBgAlt: '#444654',
        inputBg: '#40414F',
        borderSubtle: '#565869',
        textPrimary: '#ECECF1',
        textSecondary: '#9CA3AF',
        accent: '#10A37F',
        accentHover: '#0E906F'
      },
      fontFamily: {
        sans: ['"Söhne"', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif']
      },
      animation: {
        'pulse-dot': 'pulseDot 1.4s infinite ease-in-out both',
        'fade-in': 'fadeIn 0.2s ease-in',
        'slide-up': 'slideUp 0.3s ease-out'
      },
      keyframes: {
        pulseDot: {
          '0%, 80%, 100%': { transform: 'scale(0)', opacity: '0.5' },
          '40%': { transform: 'scale(1)', opacity: '1' }
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        slideUp: {
          '0%': { transform: 'translateY(8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' }
        }
      }
    }
  },
  plugins: []
}
