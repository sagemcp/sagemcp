import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CheckCircle, XCircle } from 'lucide-react'

export default function OAuthSuccess() {
  const [searchParams] = useSearchParams()
  const provider = searchParams.get('provider')
  const tenant = searchParams.get('tenant')
  const error = searchParams.get('error')

  useEffect(() => {
    console.log('OAuth Success page loaded with:', { provider, tenant, error })

    // Notify parent window that OAuth is complete (if not an error)
    if (!error && provider && tenant) {
      console.log('OAuth completed successfully, notifying parent window')
      if (window.opener) {
        console.log('Parent window found, sending message')
        window.opener.postMessage(
          { type: 'oauth-complete', provider, tenant },
          window.location.origin
        )
        console.log('Message sent to parent window')
      } else {
        console.log('No parent window found (window.opener is null)')
      }
    } else {
      console.log('OAuth not successful:', { error, provider, tenant })
    }

    // Close the popup window after a delay
    const timer = setTimeout(() => {
      console.log('Auto-closing OAuth popup window')
      window.close()
    }, 3000)

    return () => clearTimeout(timer)
  }, [error, provider, tenant])

  return (
    <div className="min-h-screen bg-[var(--bg-root)] flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-theme-surface border border-theme-default rounded-lg shadow-2xl p-8 text-center">
        {error ? (
          <>
            <XCircle className="h-16 w-16 text-error-600 mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-theme-primary mb-2">
              Authentication Failed
            </h1>
            <p className="text-theme-secondary mb-4">
              There was an error connecting to {provider}: {error}
            </p>
            <p className="text-sm text-theme-muted">
              This window will close automatically.
            </p>
          </>
        ) : (
          <>
            <CheckCircle className="h-16 w-16 text-success-600 mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-theme-primary mb-2">
              Successfully Connected!
            </h1>
            <p className="text-theme-secondary mb-4">
              Your {provider} account has been connected to tenant "{tenant}".
            </p>
            <p className="text-sm text-theme-muted">
              This window will close automatically in a few seconds.
            </p>
          </>
        )}

        <button
          onClick={() => window.close()}
          className="mt-4 btn-primary"
        >
          Close
        </button>
      </div>
    </div>
  )
}
