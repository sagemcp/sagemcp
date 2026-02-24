import React from 'react'

export type ThemeMode = 'system' | 'light' | 'dark'
export type ResolvedTheme = 'light' | 'dark'

const THEME_STORAGE_KEY = 'sagemcp.theme_mode'
const SYSTEM_DARK_QUERY = '(prefers-color-scheme: dark)'

type ThemeContextValue = {
  mode: ThemeMode
  setMode: (mode: ThemeMode) => void
  resolvedTheme: ResolvedTheme
}

const ThemeContext = React.createContext<ThemeContextValue | null>(null)

function getSystemTheme(): ResolvedTheme {
  return window.matchMedia(SYSTEM_DARK_QUERY).matches ? 'dark' : 'light'
}

function applyTheme(theme: ResolvedTheme) {
  document.documentElement.classList.toggle('dark', theme === 'dark')
  document.documentElement.style.colorScheme = theme
}

function getInitialMode(): ThemeMode {
  const savedMode = window.localStorage.getItem(THEME_STORAGE_KEY)
  if (savedMode === 'light' || savedMode === 'dark' || savedMode === 'system') {
    return savedMode
  }
  return 'system'
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = React.useState<ThemeMode>(getInitialMode)
  const [resolvedTheme, setResolvedTheme] = React.useState<ResolvedTheme>(() => (
    mode === 'system' ? getSystemTheme() : mode
  ))

  React.useEffect(() => {
    window.localStorage.setItem(THEME_STORAGE_KEY, mode)

    if (mode !== 'system') {
      setResolvedTheme(mode)
      return
    }

    const mediaQuery = window.matchMedia(SYSTEM_DARK_QUERY)
    const updateTheme = () => setResolvedTheme(mediaQuery.matches ? 'dark' : 'light')
    updateTheme()
    mediaQuery.addEventListener('change', updateTheme)

    return () => mediaQuery.removeEventListener('change', updateTheme)
  }, [mode])

  React.useEffect(() => {
    applyTheme(resolvedTheme)
  }, [resolvedTheme])

  const value = React.useMemo(() => ({ mode, setMode, resolvedTheme }), [mode, resolvedTheme])

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = React.useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return context
}

