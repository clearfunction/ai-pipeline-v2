# Fix NPM Version Resolution Issue

## Root Cause Analysis

The issue is NOT in the code generation but in npm's version resolution:

1. **Without package-lock.json**, npm install resolves to the LATEST versions that match the patterns
2. Recently, @testing-library/react released v16 which is for React 19
3. npm is picking v16 even though the package.json specifies `^14.2.1` (because of caret range)

## Why This Started Happening Now

- Testing Library v16 was recently released (for React 19 RC)
- Previous runs worked because v16 didn't exist yet
- Now npm resolves `^14.2.1` to the latest major version (16.x)

## Solutions

### Solution 1: Generate package-lock.json (BEST)
The story executor should generate a `package-lock.json` with pinned versions:

```javascript
// After generating package.json, run:
npm install --package-lock-only
// This creates package-lock.json without installing node_modules
```

### Solution 2: Use Exact Versions (Quick Fix)
Remove the caret (^) from critical dependencies:

```json
{
  "devDependencies": {
    "@testing-library/react": "14.2.1",  // No caret!
    "@testing-library/user-event": "14.5.2"  // No caret!
  }
}
```

### Solution 3: Add Resolution Rules to Workflow
Update the GitHub Actions workflow to force specific versions:

```yaml
- name: Install dependencies
  run: |
    echo "📦 Installing dependencies..."
    if [ -f "package-lock.json" ]; then
      echo "Using npm ci for faster, reliable installs..."
      npm ci
    elif [ -f "package.json" ]; then
      echo "Using npm install (no lock file found)..."
      # Force specific versions for compatibility
      npm install --save-exact @testing-library/react@14.2.1
      npm install --save-exact @testing-library/user-event@14.5.2
      npm install
    fi
```

## Immediate Fix for Current Failure

Add this to the GitHub workflow before npm install:

```yaml
- name: Fix dependency versions
  if: ${{ !contains(github.event.head_commit.message, '[skip-fix]') }}
  run: |
    # Ensure compatible testing library versions
    if [ -f "package.json" ] && [ ! -f "package-lock.json" ]; then
      echo "Fixing testing library versions for React 18 compatibility..."
      sed -i 's/"@testing-library\/react": ".*"/"@testing-library\/react": "14.2.1"/' package.json
      sed -i 's/"@testing-library\/user-event": ".*"/"@testing-library\/user-event": "14.5.2"/' package.json
    fi
```

## Long-term Fix

The story executor Lambda should:
1. Generate package.json with exact versions (no ^ or ~)
2. OR generate a package-lock.json file
3. OR use npm shrinkwrap to lock dependencies