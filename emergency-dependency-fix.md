# Emergency Fix for React Dependency Conflict

## Problem
The generated project has incompatible React and Testing Library versions:
- React 18.3.1 with @testing-library/react 16.1.0
- Error: `peer react@"^18.0.0 || ^19.0.0-rc" from @testing-library/react@16.1.0`

## Root Cause
The story executor Lambda is generating or allowing incompatible versions:
- @testing-library/react v16 is for React 19 (RC)
- @testing-library/react v14 is for React 18 (stable)

## Immediate Fix for Existing Project

### Option 1: Manual Fix in GitHub
1. Go to the repository
2. Edit `package.json` directly
3. Change these versions:
```json
"@testing-library/react": "^14.2.1",
"@testing-library/user-event": "^14.5.2",
"@testing-library/jest-dom": "^6.1.5"
```
4. Commit and push - the workflow should now work

### Option 2: Local Fix
```bash
# Clone the repo
git clone https://github.com/rakeshatcf/coach-connect-app-functional-scope-document-20250826234138.git
cd coach-connect-app-functional-scope-document-20250826234138

# Fix the versions
sed -i '' 's/"@testing-library\/react": ".*"/"@testing-library\/react": "^14.2.1"/' package.json
sed -i '' 's/"@testing-library\/user-event": ".*"/"@testing-library\/user-event": "^14.5.2"/' package.json

# Commit and push
git add package.json
git commit -m "Fix React testing library compatibility"
git push
```

## Lambda Fix Needed

The story executor needs to ensure it NEVER generates v16 of testing library with React 18:

### Check these files:
1. `/lambdas/core/story-executor/templates/react_fullstack_generator.py` - Already correct (v14.2.1)
2. `/lambdas/core/story-executor/templates/react_spa_generator.py` - Need to verify
3. Any AI-based enhancement code that might be updating versions

### Validation Rule to Add:
```python
def validate_dependencies(package_json):
    """Ensure dependency compatibility"""
    deps = package_json.get('dependencies', {})
    dev_deps = package_json.get('devDependencies', {})
    
    # If using React 18, ensure testing library is v14, not v16
    if 'react' in deps:
        react_version = deps['react']
        if react_version.startswith('^18'):
            # Force compatible testing library version
            if '@testing-library/react' in dev_deps:
                dev_deps['@testing-library/react'] = '^14.2.1'
            if '@testing-library/user-event' in dev_deps:
                dev_deps['@testing-library/user-event'] = '^14.5.2'
    
    return package_json
```

## Prevention
Add this check to the story executor before generating the final package.json to ensure versions are always compatible.