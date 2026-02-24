import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { tenantsApi } from '@/utils/api'
import { Tenant } from '@/types'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

interface TenantEditModalProps {
  isOpen: boolean
  onClose: () => void
  tenant: Tenant
}

export default function TenantEditModal({ isOpen, onClose, tenant }: TenantEditModalProps) {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState({
    name: tenant.name,
    description: tenant.description || '',
    contact_email: tenant.contact_email || '',
    is_active: tenant.is_active
  })

  useEffect(() => {
    setFormData({
      name: tenant.name,
      description: tenant.description || '',
      contact_email: tenant.contact_email || '',
      is_active: tenant.is_active
    })
  }, [tenant])

  const updateMutation = useMutation({
    mutationFn: () => tenantsApi.update(tenant.slug, {
      name: formData.name,
      slug: tenant.slug,
      description: formData.description || undefined,
      contact_email: formData.contact_email || undefined,
      is_active: formData.is_active
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenant', tenant.slug] })
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
      toast.success('Tenant updated successfully')
      onClose()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update tenant')
    }
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name.trim()) {
      toast.error('Tenant name is required')
      return
    }
    updateMutation.mutate()
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Tenant</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-theme-secondary mb-1">
                Name <span className="text-error-400">*</span>
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="input-field"
                placeholder="My Organization"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-theme-secondary mb-1">Slug</label>
              <input
                type="text"
                value={tenant.slug}
                readOnly
                className="input-field bg-theme-elevated text-theme-muted cursor-not-allowed"
              />
              <p className="text-xs text-theme-muted mt-1">Slug cannot be changed after creation</p>
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

            <div>
              <label className="block text-sm font-medium text-theme-secondary mb-1">Contact Email</label>
              <input
                type="email"
                value={formData.contact_email}
                onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                className="input-field"
                placeholder="contact@example.com"
              />
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="h-4 w-4 rounded border-theme-hover bg-theme-elevated text-accent focus:ring-accent"
              />
              <label htmlFor="is_active" className="ml-2 block text-sm text-theme-secondary">
                Active
              </label>
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
