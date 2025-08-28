# Netlify Deployment Debug Guide

## Current Issues

1. **Deployment URLs not accessible** - Sites don't exist at the expected URLs
2. **Random site IDs** - Each deployment seems to create a new site (8916, 7496, etc.)
3. **Missing dist directory** - Build output not in expected location

## Root Causes

### 1. NETLIFY_SITE_ID Not Being Set Properly
- The Lambda creates a Netlify site and gets a site ID
- It tries to add this as a GitHub secret using PyNaCl encryption
- If this fails (which it was before our PyNaCl fix), the secret isn't set
- Without NETLIFY_SITE_ID, the Netlify action creates a new site each time

### 2. Build Output Issues
For `react_fullstack` projects:
- Build output is in `client/dist` not `./dist`
- The workflow was looking in wrong directory
- Fixed by updating publish-dir to `./client/dist` for monorepos

### 3. Empty Deployments
If the build fails or produces no output:
- Netlify might create a site but with no content
- The site won't be accessible

## Solutions Applied

### 1. PyNaCl Fix (Completed)
```python
# Added to Lambda to fix layer import
if '/opt/python' not in sys.path:
    sys.path.insert(0, '/opt/python')
```

### 2. Workflow Directory Fixes (Completed)
```yaml
# For react_fullstack
publish-dir: './client/dist'

# Enhanced build process
- Detects monorepo structure
- Builds client and server separately
- Verifies output exists
- Creates fallback symlinks
```

### 3. Permission Fixes (Completed)
```yaml
enable-commit-status: false
continue-on-error: true
```

## Next Steps to Verify

1. **Check if NETLIFY_SITE_ID is set in GitHub**:
   - Go to the repository settings
   - Check Secrets and variables > Actions
   - Look for NETLIFY_SITE_ID

2. **Verify build output**:
   - Check GitHub Actions logs
   - Look at "Verify and prepare build outputs" step
   - Confirm client/dist exists

3. **Check Netlify dashboard**:
   - Log into Netlify
   - Look for sites with the project name
   - Verify if deployments are reaching the right site

## Manual Fix If Needed

If the NETLIFY_SITE_ID is missing:
1. Find the correct site in Netlify dashboard
2. Copy the site ID
3. Add it as a GitHub secret:
   ```
   Name: NETLIFY_SITE_ID
   Value: [site-id-from-netlify]
   ```

## Testing

To test if everything works:
1. Trigger a new build (push to PR)
2. Watch GitHub Actions logs
3. Check if deployment URL uses consistent site ID
4. Verify site is accessible

## Expected Behavior After Fixes

- Single Netlify site per project (not random IDs)
- Deployments go to preview URLs like: `preview-pr-XX--[site-name].netlify.app`
- Sites should be accessible immediately after deployment
- No permission errors in GitHub Actions logs