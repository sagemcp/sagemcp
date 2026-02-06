import { useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { cn } from '@/utils/cn'

interface CodeBlockProps {
  code: string
  language?: string
  className?: string
}

export function CodeBlock({ code, language, className }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={cn('relative rounded-md border border-zinc-800 bg-zinc-950', className)}>
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-zinc-800">
        {language && (
          <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-medium">{language}</span>
        )}
        <button
          onClick={handleCopy}
          className="ml-auto p-1 rounded text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
        >
          {copied ? (
            <Check className="h-3.5 w-3.5 text-success-400" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
        </button>
      </div>
      <pre className="p-3 overflow-x-auto text-xs font-mono text-zinc-300 leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  )
}
