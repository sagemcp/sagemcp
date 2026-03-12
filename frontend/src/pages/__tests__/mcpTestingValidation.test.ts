import { describe, expect, it } from 'vitest'
import {
  collectJsonPropertyPaths,
  mapValidationErrorsToPropertyTokenIndices,
  resolvePropertyPathForError,
  type ValidationErrorDetail,
} from '../mcpTestingValidation'

describe('mcpTestingValidation helpers', () => {
  it('collects JSON property paths in source order', () => {
    const jsonText = `{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "prompts/get",
  "params": {
    "name": "test_prompt",
    "arguments": {
      "id": "1",
      "method": "oops"
    }
  }
}`

    expect(collectJsonPropertyPaths(jsonText)).toEqual([
      '/jsonrpc',
      '/id',
      '/method',
      '/params',
      '/params/name',
      '/params/arguments',
      '/params/arguments/id',
      '/params/arguments/method',
    ])
  })

  it('falls back to the nearest existing ancestor path for missing keys', () => {
    const propertyPaths = [
      '/jsonrpc',
      '/id',
      '/method',
      '/params',
      '/params/name',
      '/params/arguments',
    ]

    expect(resolvePropertyPathForError('/params/arguments/id', propertyPaths)).toBe('/params/arguments')
  })

  it('maps nested argument errors to nested property token indices', () => {
    const jsonText = `{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "prompts/get",
  "params": {
    "name": "test_prompt",
    "arguments": {
      "id": "1",
      "method": "oops"
    }
  }
}`
    const errors: ValidationErrorDetail[] = [
      {
        message: 'arguments.method is not allowed',
        path: '/params/arguments/method',
      },
    ]

    const mapped = mapValidationErrorsToPropertyTokenIndices(jsonText, errors)
    expect(Array.from(mapped.keys())).toEqual([7])
    expect(mapped.get(7)?.map((error) => error.message)).toEqual(['arguments.method is not allowed'])
  })

  it('maps missing nested argument errors to the arguments container token index', () => {
    const jsonText = `{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "prompts/get",
  "params": {
    "name": "test_prompt",
    "arguments": {}
  }
}`
    const errors: ValidationErrorDetail[] = [
      {
        message: 'arguments.id is required',
        path: '/params/arguments/id',
      },
    ]

    const mapped = mapValidationErrorsToPropertyTokenIndices(jsonText, errors)
    expect(Array.from(mapped.keys())).toEqual([5])
    expect(mapped.get(5)?.map((error) => error.message)).toEqual(['arguments.id is required'])
  })

  it('uses the last matching token index for duplicate property paths', () => {
    const jsonText = `{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "known_tool",
    "name": "",
    "arguments": {}
  }
}`
    const errors: ValidationErrorDetail[] = [
      {
        message: 'Unknown tool "".',
        path: '/params/name',
      },
    ]

    const mapped = mapValidationErrorsToPropertyTokenIndices(jsonText, errors)
    expect(Array.from(mapped.keys())).toEqual([5])
    expect(mapped.get(5)?.map((error) => error.message)).toEqual(['Unknown tool "".'])
  })

  it('stores multiple errors on the same token index', () => {
    const jsonText = `{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "prompts/get",
  "params": {
    "name": "test_prompt",
    "arguments": {}
  }
}`
    const errors: ValidationErrorDetail[] = [
      {
        message: 'arguments.id is required',
        path: '/params/arguments/id',
      },
      {
        message: 'arguments.repo is required',
        path: '/params/arguments/repo',
      },
    ]

    const mapped = mapValidationErrorsToPropertyTokenIndices(jsonText, errors)
    expect(Array.from(mapped.keys())).toEqual([5])
    expect(mapped.get(5)?.map((error) => error.message)).toEqual([
      'arguments.id is required',
      'arguments.repo is required',
    ])
  })
})
