import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import {
  Plus,
  Search,
  MoreVertical,
  Edit,
  Trash2,
  ExternalLink,
  Building2,
  Mail,
  Calendar,
  Users
} from 'lucide-react'
import { tenantsApi, connectorsApi } from '@/utils/api'
import { Tenant, TenantCreate } from '@/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/sage/empty-state'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter } from '@/components/ui/sheet'

const tenantSchema = z.object({
  slug: z.string()
    .min(2, 'Slug must be at least 2 characters')
    .max(50, 'Slug must be less than 50 characters')
    .regex(/^[a-z0-9-]+$/, 'Slug can only contain lowercase letters, numbers, and hyphens'),
  name: z.string().min(1, 'Name is required').max(100, 'Name must be less than 100 characters'),
  description: z.string().optional(),
  contact_email: z.string().email('Invalid email address').optional().or(z.literal('')),
})

type TenantFormData = z.infer<typeof tenantSchema>

const TenantSheet = ({
  open,
  onOpenChange,
  tenant
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  tenant?: Tenant
}) => {
  const queryClient = useQueryClient()
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset
  } = useForm<TenantFormData>({
    resolver: zodResolver(tenantSchema),
    defaultValues: tenant ? {
      slug: tenant.slug,
      name: tenant.name,
      description: tenant.description || '',
      contact_email: tenant.contact_email || '',
    } : undefined
  })

  const createMutation = useMutation({
    mutationFn: (data: TenantCreate) =>
      tenant ? tenantsApi.update(tenant.slug, data) : tenantsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
      toast.success(tenant ? 'Tenant updated successfully' : 'Tenant created successfully')
      onOpenChange(false)
      reset()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || (tenant ? 'Failed to update tenant' : 'Failed to create tenant'))
    }
  })

  const onSubmit = (data: TenantFormData) => {
    const submitData: TenantCreate = {
      ...data,
      contact_email: data.contact_email || undefined
    }
    createMutation.mutate(submitData)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent onClose={() => onOpenChange(false)}>
        <SheetHeader>
          <SheetTitle>{tenant ? 'Edit Tenant' : 'Create Tenant'}</SheetTitle>
          <SheetDescription>
            {tenant ? 'Update tenant configuration' : 'Set up a new multi-tenant MCP environment'}
          </SheetDescription>
        </SheetHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex-1 flex flex-col">
          <div className="flex-1 px-6 py-4 space-y-4 overflow-y-auto">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Slug *</label>
              <input
                {...register('slug')}
                className="input-field"
                placeholder="my-tenant"
                disabled={!!tenant}
              />
              {errors.slug && <p className="mt-1 text-sm text-error-400">{errors.slug.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Name *</label>
              <input {...register('name')} className="input-field" placeholder="My Tenant" />
              {errors.name && <p className="mt-1 text-sm text-error-400">{errors.name.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Description</label>
              <textarea
                {...register('description')}
                className="input-field"
                rows={3}
                placeholder="Brief description of this tenant..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Contact Email</label>
              <input
                {...register('contact_email')}
                type="email"
                className="input-field"
                placeholder="contact@example.com"
              />
              {errors.contact_email && <p className="mt-1 text-sm text-error-400">{errors.contact_email.message}</p>}
            </div>
          </div>

          <SheetFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : (tenant ? 'Update' : 'Create')}
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  )
}

const TenantCard = ({ tenant }: { tenant: Tenant }) => {
  const [showMenu, setShowMenu] = useState(false)
  const [showEditSheet, setShowEditSheet] = useState(false)
  const queryClient = useQueryClient()

  const { data: connectors = [] } = useQuery({
    queryKey: ['connectors', tenant.slug],
    queryFn: () => connectorsApi.list(tenant.slug).then(res => res.data),
  })

  const deleteMutation = useMutation({
    mutationFn: (slug: string) => tenantsApi.delete(slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
      toast.success('Tenant deleted successfully')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete tenant')
    }
  })

  const handleDelete = () => {
    if (confirm(`Are you sure you want to delete tenant "${tenant.name}"? This will also delete all associated connectors.`)) {
      deleteMutation.mutate(tenant.slug)
    }
    setShowMenu(false)
  }

  return (
    <>
      <div className="rounded-lg border border-zinc-800 bg-surface-elevated hover:border-zinc-700 transition-colors">
        <div className="p-5">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <Link
                  to={`/tenants/${tenant.slug}`}
                  className="text-base font-semibold text-zinc-100 hover:text-accent transition-colors"
                >
                  {tenant.name}
                </Link>
                <Badge variant={tenant.is_active ? 'healthy' : 'idle'}>
                  {tenant.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </div>
              <p className="text-xs text-zinc-500 font-mono mt-0.5">{tenant.slug}</p>
              {tenant.description && (
                <p className="text-sm text-zinc-400 mt-2 line-clamp-2">{tenant.description}</p>
              )}
            </div>

            <div className="relative ml-2">
              <button
                onClick={() => setShowMenu(!showMenu)}
                className="p-1 rounded hover:bg-zinc-800 text-zinc-500 transition-colors"
              >
                <MoreVertical className="h-4 w-4" />
              </button>
              {showMenu && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
                  <div className="absolute right-0 mt-1 w-44 rounded-md bg-zinc-800 border border-zinc-700 py-1 z-20 shadow-elevated">
                    <Link
                      to={`/tenants/${tenant.slug}`}
                      className="flex items-center px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-700"
                      onClick={() => setShowMenu(false)}
                    >
                      <ExternalLink className="h-3.5 w-3.5 mr-2" />
                      View Details
                    </Link>
                    <button
                      onClick={() => { setShowEditSheet(true); setShowMenu(false) }}
                      className="flex items-center w-full px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-700"
                    >
                      <Edit className="h-3.5 w-3.5 mr-2" />
                      Edit
                    </button>
                    <button
                      onClick={handleDelete}
                      disabled={deleteMutation.isPending}
                      className="flex items-center w-full px-3 py-2 text-sm text-error-400 hover:bg-zinc-700 disabled:opacity-50"
                    >
                      <Trash2 className="h-3.5 w-3.5 mr-2" />
                      {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Footer meta */}
          <div className="flex items-center gap-4 mt-4 pt-3 border-t border-zinc-800">
            {connectors.length > 0 && (
              <span className="text-xs text-zinc-500">
                <span className="text-zinc-400 font-medium">{connectors.length}</span> connector{connectors.length !== 1 ? 's' : ''}
              </span>
            )}
            {tenant.contact_email && (
              <div className="flex items-center gap-1 text-xs text-zinc-500">
                <Mail className="h-3 w-3" />
                <span className="truncate max-w-[140px]">{tenant.contact_email}</span>
              </div>
            )}
            {tenant.created_at && (
              <div className="flex items-center gap-1 text-xs text-zinc-500 ml-auto">
                <Calendar className="h-3 w-3" />
                <span>{new Date(tenant.created_at).toLocaleDateString()}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <TenantSheet open={showEditSheet} onOpenChange={setShowEditSheet} tenant={tenant} />
    </>
  )
}

export default function Tenants() {
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateSheet, setShowCreateSheet] = useState(false)

  const { data: tenants = [], isLoading } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantsApi.list().then(res => res.data)
  })

  const filteredTenants = tenants.filter(tenant =>
    tenant.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    tenant.slug.toLowerCase().includes(searchQuery.toLowerCase()) ||
    tenant.description?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">Tenants</h1>
          <p className="text-sm text-zinc-500 mt-1">Manage your multi-tenant configurations</p>
        </div>
        <Button onClick={() => setShowCreateSheet(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create Tenant
        </Button>
      </div>

      {/* Search and count */}
      <div className="flex items-center gap-4">
        <div className="flex-1 max-w-md relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
          <input
            type="text"
            placeholder="Search tenants..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-field pl-10"
          />
        </div>
        <div className="flex items-center gap-2 text-sm text-zinc-500">
          <Users className="h-4 w-4" />
          <span>{filteredTenants.length} tenant{filteredTenants.length !== 1 ? 's' : ''}</span>
        </div>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="rounded-lg border border-zinc-800 bg-surface-elevated p-5">
              <Skeleton className="h-5 w-3/4 mb-2" />
              <Skeleton className="h-3 w-1/2 mb-4" />
              <Skeleton className="h-3 w-full" />
            </div>
          ))}
        </div>
      ) : filteredTenants.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTenants.map((tenant) => (
            <TenantCard key={tenant.id} tenant={tenant} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={Building2}
          title={searchQuery ? 'No tenants found' : 'No tenants yet'}
          description={searchQuery ? 'Try adjusting your search criteria' : 'Get started by creating your first tenant'}
          action={!searchQuery ? { label: 'Create Tenant', onClick: () => setShowCreateSheet(true) } : undefined}
        />
      )}

      <TenantSheet open={showCreateSheet} onOpenChange={setShowCreateSheet} />
    </div>
  )
}
