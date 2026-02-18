import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { connectorsApi } from '@/utils/api'
import { Connector } from '@/types'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

interface ConnectorEditModalProps {
  isOpen: boolean
  onClose: () => void
  connector: Connector
  tenantSlug: string
}

export default function ConnectorEditModal({
  isOpen,
  onClose,
  connector,
  tenantSlug
}: ConnectorEditModalProps) {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState({
    name: connector.name,
    description: connector.description || ''
  })

  useEffect(() => {
    setFormData({
      name: connector.name,
      description: connector.description || ''
    })
  }, [connector])

  const updateMutation = useMutation({
    mutationFn: () => connectorsApi.update(tenantSlug, connector.id, {
      connector_type: connector.connector_type,
      name: formData.name,
      description: formData.description || undefined,
      configuration: connector.configuration
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connectors', tenantSlug] })
      toast.success('Connector updated successfully')
      onClose()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update connector')
    }
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name.trim()) {
      toast.error('Connector name is required')
      return
    }
    updateMutation.mutate()
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Connector</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-theme-secondary mb-1">Connector Type</label>
              <input
                type="text"
                value={connector.connector_type}
                readOnly
                className="input-field bg-theme-elevated text-theme-muted cursor-not-allowed capitalize"
              />
              <p className="text-xs text-theme-muted mt-1">Connector type cannot be changed</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-theme-secondary mb-1">
                Name <span className="text-error-400">*</span>
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="input-field"
                placeholder="My GitHub Connector"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-theme-secondary mb-1">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="input-field"
                placeholder="Optional description"
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={updateMutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
