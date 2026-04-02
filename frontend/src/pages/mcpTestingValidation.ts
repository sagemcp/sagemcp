import { parseTree, type ParseError } from 'jsonc-parser'

export interface ValidationErrorDetail {
  message: string
  path?: string
  propertyName?: string
  offset?: number
}

export function collectJsonPropertyPaths(jsonText: string): string[] {
  const syntaxErrors: ParseError[] = []
  const root = parseTree(jsonText, syntaxErrors, {
    allowTrailingComma: true,
    disallowComments: false,
  })
  if (!root) {
    return []
  }

  const propertyPaths: string[] = []

  const visitNode = (node: any, path: string[]) => {
    if (node.type === 'property') {
      const keyNode = node.children?.[0]
      const valueNode = node.children?.[1]
      const propertyName = typeof keyNode?.value === 'string' ? keyNode.value : null
      if (!propertyName) {
        return
      }

      const nextPath = [...path, propertyName]
      propertyPaths.push(`/${nextPath.join('/')}`)
      if (valueNode) {
        visitNode(valueNode, nextPath)
      }
      return
    }

    if (!Array.isArray(node.children)) {
      return
    }

    if (node.type === 'array') {
      node.children.forEach((child: any, index: number) => {
        visitNode(child, [...path, String(index)])
      })
      return
    }

    node.children.forEach((child: any) => visitNode(child, path))
  }

  visitNode(root, [])
  return propertyPaths
}

export function resolvePropertyPathForError(
  errorPath: string | undefined,
  propertyPaths: string[]
): string | null {
  if (!errorPath || errorPath === '/') {
    return null
  }

  const propertyPathSet = new Set(propertyPaths)
  let candidate = errorPath

  while (candidate) {
    if (propertyPathSet.has(candidate)) {
      return candidate
    }

    const lastSlashIndex = candidate.lastIndexOf('/')
    if (lastSlashIndex <= 0) {
      break
    }
    candidate = candidate.slice(0, lastSlashIndex)
  }

  return null
}

export function mapValidationErrorsToPropertyTokenIndices(
  jsonText: string,
  errors: ValidationErrorDetail[]
): Map<number, ValidationErrorDetail[]> {
  const propertyPaths = collectJsonPropertyPaths(jsonText)
  const tokenIndexMap = new Map<number, ValidationErrorDetail[]>()

  for (const error of errors) {
    const resolvedPath = resolvePropertyPathForError(error.path, propertyPaths)
    if (!resolvedPath) {
      continue
    }

    const tokenIndex = propertyPaths.lastIndexOf(resolvedPath)
    if (tokenIndex === -1) {
      continue
    }

    const existingErrors = tokenIndexMap.get(tokenIndex) ?? []
    tokenIndexMap.set(tokenIndex, [...existingErrors, error])
  }

  return tokenIndexMap
}
