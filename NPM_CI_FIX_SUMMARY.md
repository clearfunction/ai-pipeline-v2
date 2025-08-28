# NPM CI Fix Summary - Package Lock JSON Issue

## Problem
GitHub Actions was failing with:
```
npm error `npm ci` can only install packages when your package.json and package-lock.json are in sync
```

## Root Cause
The template generators were creating **stub package-lock.json files** that contained only minimal structure without actual dependency resolution data. These stub files caused `npm ci` to fail because they didn't match the package.json dependencies.

Example of the problematic stub:
```json
{
  "name": "project-name",
  "version": "1.0.0",
  "lockfileVersion": 3,
  "requires": true,
  "packages": {
    "": {
      "name": "project-name",
      "version": "1.0.0",
      "workspaces": ["client", "server", "shared"]
    }
  }
}
```

## Solution Applied
**Removed stub package-lock.json generation from all template generators.**

### Files Modified
1. `lambdas/core/story-executor/templates/react_fullstack_generator.py`
   - Removed `_get_root_package_lock_json()` method
   - Removed package-lock.json from root_files dict

2. `lambdas/core/story-executor/templates/react_spa_generator.py`
   - Removed `_get_package_lock_json()` method
   - Removed package-lock.json from templates dict

3. `lambdas/core/story-executor/templates/vue_spa_generator.py`
   - Removed `_get_package_lock_json()` method
   - Removed package-lock.json from templates dict

4. `lambdas/core/story-executor/templates/node_api_generator.py`
   - Removed `_get_package_lock_json()` method
   - Removed package-lock.json from templates dict

## How It Works Now
1. **First GitHub Actions run**: No package-lock.json exists → workflow uses `npm install`
2. **npm install** creates a proper package-lock.json with actual dependency resolution
3. **Subsequent runs**: Real package-lock.json exists → workflow uses `npm ci` successfully

The GitHub orchestrator already has smart detection:
```javascript
if [ -f "package-lock.json" ]; then
  echo "Using npm ci for faster, reliable installs..."
  npm ci
elif [ -f "package.json" ]; then
  echo "Using npm install (no lock file found)..."
  npm install
fi
```

## Testing
✅ Verified all generators no longer produce package-lock.json files
✅ Confirmed package.json files are still generated correctly
✅ Tested with all four template generators:
- React Fullstack
- React SPA
- Vue SPA
- Node API

## Deployment
✅ Lambda deployed: `ai-pipeline-v2-story-executor-dev`
- Last Modified: 2025-08-27T14:59:57.000+0000

## Impact
New projects generated will:
- Not have stub package-lock.json files
- Use `npm install` on first GitHub Actions run
- Generate proper package-lock.json files automatically
- Use `npm ci` on subsequent runs for faster, reliable installs

## Why This Fix Is Correct
- Stub package-lock.json files were incomplete and invalid for `npm ci`
- npm is designed to generate package-lock.json automatically on `npm install`
- The GitHub workflow already handles both scenarios intelligently
- This aligns with npm best practices