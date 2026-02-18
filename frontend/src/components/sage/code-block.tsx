import { useMemo, useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { Highlight, PrismTheme } from 'prism-react-renderer'
import { useTheme } from '@/components/theme-provider'
import { cn } from '@/utils/cn'

interface CodeBlockProps {
  code: string
  language?: string
  className?: string
}

export function CodeBlock({ code, language, className }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)
  const { resolvedTheme } = useTheme()
  const highlightTheme = useMemo<PrismTheme>(() => ({
    plain: {
      color: resolvedTheme === 'dark' ? '#fafafa' : '#18181b',
      backgroundColor: 'transparent',
    },
    styles: [
      { types: ['property'], style: { color: '#dc2626' } },
      { types: ['string'], style: { color: '#16a34a' } },
      { types: ['null'], style: { color: '#7e22ce' } },
      { types: ['boolean', 'number'], style: { color: 'rgb(183, 107, 1)' } },
      { types: ['punctuation'], style: { color: resolvedTheme === 'dark' ? '#94a3b8' : '#64748b' } },
    ],
  }), [resolvedTheme])

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={cn('relative rounded-md border border-theme-default bg-theme-surface', className)}>
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-theme-default">
        {language && (
          <span className="text-[10px] uppercase tracking-wider text-theme-muted font-medium">{language}</span>
        )}
        <button
          onClick={handleCopy}
          className="ml-auto p-1 rounded text-theme-muted hover:text-theme-secondary hover:bg-theme-elevated transition-colors"
        >
          {copied ? (
            <Check className="h-3.5 w-3.5 text-success-400" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
        </button>
      </div>
      <Highlight
        theme={highlightTheme}
        code={code}
        language={language ?? 'text'}
      >
        {({ className: prismClassName, style, tokens, getLineProps, getTokenProps }) => (
          <pre
            className={cn('p-3 overflow-x-auto text-xs font-mono leading-relaxed', prismClassName)}
            style={{ ...style, margin: 0, background: 'transparent' }}
          >
            <code>
              {tokens.map((line, i) => (
                <div key={i} {...getLineProps({ line })}>
                  {line.map((token, key) => (
                    <span key={key} {...getTokenProps({ token })} />
                  ))}
                </div>
              ))}
            </code>
          </pre>
        )}
      </Highlight>
    </div>
  )
}
