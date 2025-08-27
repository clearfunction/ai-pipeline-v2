# Manual Testing Checklist Template

**Project**: _______________  
**Tech Stack**: _______________  
**Environment**: dev  
**Tester**: _______________  
**Date**: _______________  

## Deployment URLs

- **Frontend**: _______________
- **Backend**: _______________  
- **GitHub Repository**: _______________
- **Pull Request**: _______________

## Pre-Testing Setup

- [ ] All deployment URLs are accessible
- [ ] Test data is properly seeded
- [ ] Browser developer tools are open for debugging
- [ ] Testing environment is confirmed (dev/staging)

## User Story Validation

*Review the GitHub PR description for specific acceptance criteria and test each one*

### Story 1: _______________

**Acceptance Criteria**:
1. [ ] _______________
2. [ ] _______________
3. [ ] _______________

**Test Results**:
- **Status**: ✅ Pass / ❌ Fail / ⚠️ Partial
- **Notes**: _______________

### Story 2: _______________

**Acceptance Criteria**:
1. [ ] _______________
2. [ ] _______________
3. [ ] _______________

**Test Results**:
- **Status**: ✅ Pass / ❌ Fail / ⚠️ Partial
- **Notes**: _______________

## Frontend Testing (if applicable)

### Basic Functionality
- [ ] **Page Load**: Application loads without errors
- [ ] **Navigation**: All routes/pages are accessible
- [ ] **Responsive Design**: Works on desktop, tablet, mobile
- [ ] **UI Components**: Forms, buttons, modals work correctly
- [ ] **Error Handling**: Graceful error messages displayed

### User Experience
- [ ] **Visual Design**: Clean, professional appearance
- [ ] **Usability**: Intuitive navigation and interactions
- [ ] **Accessibility**: Basic keyboard navigation works
- [ ] **Loading States**: Appropriate loading indicators
- [ ] **Form Validation**: Input validation works correctly

### Performance
- [ ] **Load Time**: Initial page load < 3 seconds
- [ ] **Interactivity**: Smooth interactions, no lag
- [ ] **Bundle Size**: No obvious performance issues

## Backend Testing (if applicable)

### API Endpoints
- [ ] **Health Check**: `GET /health` returns 200
- [ ] **API Documentation**: Docs endpoint accessible
- [ ] **Base Endpoints**: Core API endpoints respond correctly
- [ ] **Error Responses**: Proper HTTP status codes returned
- [ ] **Response Times**: API responses < 2 seconds

### Data Operations
- [ ] **Create Operations**: POST requests work correctly
- [ ] **Read Operations**: GET requests return expected data
- [ ] **Update Operations**: PUT/PATCH requests work correctly
- [ ] **Delete Operations**: DELETE requests work correctly
- [ ] **Data Validation**: Invalid inputs return appropriate errors

## Integration Testing

### Frontend-Backend Communication (if full-stack)
- [ ] **API Calls**: Frontend successfully calls backend
- [ ] **Data Flow**: Data flows correctly between services
- [ ] **Error Handling**: Frontend handles backend errors gracefully
- [ ] **Authentication**: Auth flow works end-to-end (if applicable)

### Third-Party Services
- [ ] **External APIs**: Any external service integrations work
- [ ] **File Uploads**: File handling works correctly (if applicable)
- [ ] **Database**: Data persistence works as expected

## Cross-Browser Testing (Frontend)

### Desktop Browsers
- [ ] **Chrome**: Full functionality confirmed
- [ ] **Firefox**: Full functionality confirmed  
- [ ] **Safari**: Full functionality confirmed (if available)
- [ ] **Edge**: Full functionality confirmed (if available)

### Mobile Testing
- [ ] **Mobile Chrome**: Responsive design works
- [ ] **Mobile Safari**: Responsive design works (if available)
- [ ] **Touch Interactions**: Touch/swipe gestures work properly

## Security Testing

- [ ] **Input Sanitization**: No XSS vulnerabilities in forms
- [ ] **Authentication**: Login/logout works correctly (if applicable)
- [ ] **Authorization**: Proper access controls (if applicable)
- [ ] **HTTPS**: All communications over secure connections
- [ ] **Error Messages**: No sensitive information exposed

## Performance Testing

### Load Times
- **Frontend Load**: _____ seconds
- **Backend Health**: _____ seconds
- **Largest API Call**: _____ seconds

### Resource Usage
- [ ] **Network**: No excessive network requests
- [ ] **Memory**: No obvious memory leaks
- [ ] **CPU**: No excessive CPU usage

## Issues Found

### Issue 1
- **Severity**: High / Medium / Low
- **Description**: _______________
- **Steps to Reproduce**: 
  1. _______________
  2. _______________
  3. _______________
- **Expected Result**: _______________
- **Actual Result**: _______________
- **Browser/Environment**: _______________

### Issue 2
- **Severity**: High / Medium / Low
- **Description**: _______________
- **Steps to Reproduce**: 
  1. _______________
  2. _______________
  3. _______________
- **Expected Result**: _______________
- **Actual Result**: _______________
- **Browser/Environment**: _______________

## Overall Assessment

### Quality Metrics
- **Functionality**: ___/10
- **User Experience**: ___/10
- **Performance**: ___/10
- **Reliability**: ___/10
- **Overall Score**: ___/10

### Recommendation
- [ ] **✅ Approve**: Ready for production
- [ ] **⚠️ Approve with Minor Issues**: Deploy with noted issues
- [ ] **❌ Reject**: Major issues must be fixed before deployment

### Summary
_______________

### Additional Notes
_______________

---

## Next Steps

1. **If Approved**: Comment on GitHub PR with approval
2. **If Issues Found**: Create detailed GitHub issue with:
   - Screenshots/videos of issues
   - Steps to reproduce
   - Environment details
   - Severity assessment

3. **Follow-up**: Monitor for fixes and retest as needed

**Testing Completed By**: _______________  
**Date Completed**: _______________  
**Total Testing Time**: _____ minutes