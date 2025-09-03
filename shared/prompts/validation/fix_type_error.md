# Fix TypeScript Type Errors

You need to fix TypeScript type errors in the code.

## Current Type Errors:
{{errors}}

## File Context:
```typescript
{{file_content}}
```

## Available Types and Interfaces:
{{available_types}}

## Requirements:
1. Fix all TypeScript type errors
2. Add missing type annotations
3. Fix type mismatches
4. Add interface definitions if needed
5. Use proper generic types
6. Fix function parameter and return types
7. Handle null/undefined properly

## Strategies:
- Add explicit type annotations where missing
- Create interfaces for complex objects
- Use union types for multiple possible values
- Add type guards for runtime checks
- Use generics for reusable components
- Handle optional properties with ?
- Use type assertions only when necessary

## Output Format:
Provide the complete fixed file with all type errors resolved.

FILE: {{file_path}}
TYPE: source
LANGUAGE: typescript
---
[Fixed TypeScript code here]
---
END_FILE

## Important:
- Don't use 'any' type unless absolutely necessary
- Preserve all functionality
- Make types as specific as possible
- Follow TypeScript best practices