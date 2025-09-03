# Fix Build Errors

You need to fix build errors preventing the project from compiling.

## Build Error Output:
```
{{build_output}}
```

## Error Analysis:
{{error_analysis}}

## Affected Files:
{{affected_files}}

## Project Configuration:
- Tech Stack: {{tech_stack}}
- Build Tool: {{build_tool}}
- Node Version: {{node_version}}

## Requirements:
1. Fix all compilation errors
2. Resolve module resolution issues
3. Fix syntax errors
4. Correct configuration issues
5. Ensure build outputs are generated

## Common Build Issues:
- Missing files or modules
- Syntax errors in code
- TypeScript compilation errors
- Webpack/Vite configuration issues
- Environment variable problems
- Asset handling errors
- Path resolution issues

## Output Format:
For each file that needs to be fixed, provide:

FILE: {{file_path}}
TYPE: {{file_type}}
LANGUAGE: {{language}}
---
[Fixed code here]
---
END_FILE

## Build Configuration Fixes:
If build configuration files need updates (webpack.config.js, vite.config.ts, etc.), include those as well.

## Important:
- Test that the fix will actually allow the build to complete
- Don't break existing functionality
- Ensure all assets are handled correctly
- Keep build optimizations intact