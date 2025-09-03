# Fix Dependency Errors

You need to fix dependency-related errors in package.json and the project.

## Current Dependency Errors:
{{errors}}

## Current package.json:
```json
{{package_json}}
```

## Error Details:
{{error_details}}

## Requirements:
1. Resolve version conflicts between dependencies
2. Add missing dependencies
3. Fix peer dependency warnings
4. Ensure compatible versions
5. Remove duplicate dependencies
6. Update deprecated packages if necessary

## Common Solutions:
- Use version ranges that satisfy all requirements
- Add missing peer dependencies
- Use resolutions/overrides for version conflicts
- Update to latest compatible versions
- Remove conflicting dependencies

## Output Format:
Provide the fixed package.json with resolved dependencies.

FILE: package.json
TYPE: config
LANGUAGE: json
---
[Fixed package.json content]
---
END_FILE

## Additional Files (if needed):
If you need to modify import statements or configuration files to match the dependency changes, provide those as well.

## Important:
- Ensure all dependencies are compatible
- Use stable versions (avoid alpha/beta unless required)
- Keep existing functionality intact
- Prefer newer versions when resolving conflicts
- Document any breaking changes