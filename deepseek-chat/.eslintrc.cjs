module.exports = {
  root: true,
  env: {
    browser: true,
    es2020: true,
    node: true,
  },
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true,
    },
  },
  settings: {
    react: {
      version: 'detect',
    },
  },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
    'prettier',
  ],
  rules: {
    // React 规则
    'react/react-in-jsx-scope': 'off',
    'react/prop-types': 'off',
    
    // React Hooks 实验性规则（对已有代码过于严格，降级为 warn）
    'react-hooks/refs': 'off',
    'react-hooks/purity': 'off',
    'react-hooks/set-state-in-effect': 'off',
    'react-hooks/immutability': 'off',
    'react-hooks/set-state-in-render': 'off',
    
    // TypeScript 规则
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/explicit-module-boundary-types': 'off',
    '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    
    // 通用规则
    'no-console': ['warn', { allow: ['warn', 'error', 'info', 'log'] }],
    'no-unused-vars': 'off', // 由 @typescript-eslint/no-unused-vars 处理
  },
  ignorePatterns: [
    'dist/',
    'node_modules/',
    '*.config.*',
    '*.cjs',
  ],
}
