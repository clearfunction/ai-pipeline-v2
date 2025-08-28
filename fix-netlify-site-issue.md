# Fix Netlify Site Issue - Multiple Sites Being Created

## Problem
Each GitHub Actions run is creating a NEW Netlify site (with IDs like 7160, 7496, 8916) instead of using the same site. This happens because:
1. The Lambda creates a Netlify site and adds NETLIFY_SITE_ID as a GitHub secret
2. But the PR workflow starts immediately and doesn't see the secret yet
3. Without NETLIFY_SITE_ID, the Netlify action creates a new site each time

## Immediate Manual Fix

### Step 1: Find the Correct Netlify Site
1. Go to https://app.netlify.com
2. Look for sites named like `coach-connect-app-functional-scope-document-*`
3. Find the FIRST one created (or pick one to be the main site)
4. Copy its Site ID from the Site Settings

### Step 2: Add GitHub Secret Manually
1. Go to the GitHub repository: https://github.com/rakeshatcf/coach-connect-app-functional-scope-document-20250826234138
2. Go to Settings → Secrets and variables → Actions
3. Check if NETLIFY_SITE_ID already exists
   - If YES: Update it with the correct site ID
   - If NO: Create new secret with:
     - Name: `NETLIFY_SITE_ID`
     - Value: The site ID you copied from Netlify

### Step 3: Trigger a New Build
1. Go to the open PR
2. Make a small change (like add a comment) and push
3. This will trigger a new workflow run that WILL use the correct site ID

## Long-term Code Fix

The Lambda needs to be updated to handle this timing issue:

### Option 1: Add Warning in Workflow
```yaml
- name: Check for Netlify Site ID
  run: |
    if [ -z "${{ secrets.NETLIFY_SITE_ID }}" ]; then
      echo "⚠️  WARNING: NETLIFY_SITE_ID not found!"
      echo "A new Netlify site will be created."
      echo "To fix: Add NETLIFY_SITE_ID secret to the repository"
    fi
```

### Option 2: Commit Workflow Files First
Instead of creating a PR immediately:
1. Commit all files including workflows to the branch
2. Wait a few seconds for secrets to propagate
3. Then create the PR

### Option 3: Use Netlify API in Workflow
Instead of relying on the GitHub Action's auto-create:
```yaml
- name: Get or Create Netlify Site
  run: |
    # Use Netlify API to check if site exists
    # Create only if it doesn't exist
    # This ensures consistent site ID
```

## Verification

After fixing, all deployments should go to the SAME Netlify site:
- URLs will be consistent: `preview-pr-XX--[site-name].netlify.app`
- No more random IDs (7160, 7496, etc.)
- All PR previews will be on the same site

## Clean Up

After fixing, you can delete the extra Netlify sites that were created:
1. Go to https://app.netlify.com
2. Find the duplicate sites (with the random IDs)
3. Go to each site's Settings → Delete site
4. Keep only the main site with the correct ID