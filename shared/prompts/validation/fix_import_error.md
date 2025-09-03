# Fix Import/Export Errors

You need to fix import and export errors in a TypeScript/JavaScript project.

## Current Errors:
{{errors}}

## File Context:
```{{language}}
{{file_content}}
```

## Existing Project Structure:
{{project_structure}}

## Requirements:
1. Fix all import path errors
2. Ensure all imports resolve correctly
3. Add missing imports for undefined references
4. Remove unused imports
5. Fix circular dependencies if present
6. Use correct relative paths (../, ./, etc.)
7. Ensure named vs default imports are correct

## Output Format:
Provide the complete fixed file with all import errors resolved.

FILE: {{file_path}}
TYPE: source
LANGUAGE: {{language}}
---
[Fixed code here]
---
END_FILE

## Important:
- Preserve all existing functionality
- Don't change the logic, only fix imports
- Ensure TypeScript types are imported correctly
- Check that all exported items exist in their source files