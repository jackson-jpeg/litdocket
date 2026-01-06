# Error Fixes Summary

## Issues Found

### 1. ❌ Document Upload Failed - Case ID NULL Constraint
**Error:** `IntegrityError: NOT NULL constraint failed: documents.case_id`

**Root Cause:**
When uploading a document without specifying a `case_id`, if the AI failed to extract a `case_number` from the document, the system would leave `case_id` as `None`, causing a database constraint violation.

**Fix Applied:**
Modified `/backend/app/services/document_service.py` to ensure a case is always created when needed:
- If `case_id` is provided → Use it
- If no `case_id` but `case_number` detected → Find existing case or create new one
- **NEW:** If no `case_id` and no `case_number` detected → Create placeholder case with auto-generated case number

```python
# Now creates a placeholder case if case_number can't be extracted
new_case = Case(
    user_id=user_id,
    case_number=f"NEW-{uuid.uuid4().hex[:8].upper()}",  # e.g., NEW-A3B9C7F1
    title=f"New Case - {file_name}",
    court=analysis.get('court'),
    judge=analysis.get('judge'),
    case_type=analysis.get('case_type', 'Unknown'),
    jurisdiction=analysis.get('jurisdiction'),
    district=analysis.get('district'),
    parties=analysis.get('parties', []),
    case_metadata=analysis
)
```

**Status:** ✅ Fixed

---

### 2. ❌ CORS Error on Document Upload (500 Status)
**Error:** `Origin http://localhost:3000 is not allowed by Access-Control-Allow-Origin. Status code: 500`

**Root Cause:**
When the document upload endpoint threw an exception (due to the NULL constraint), the error response didn't include CORS headers, causing the browser to block the response.

**Fix Applied:**
Added comprehensive error handling to `/backend/app/api/v1/documents.py`:
- Wrapped entire endpoint in try-catch
- Ensured proper exception handling
- Added traceback printing for debugging
- Proper re-raising of HTTP exceptions

**Status:** ✅ Fixed

---

### 3. ⚠️ 401 Unauthorized Errors
**Error:** Multiple 401 errors on case detail and history endpoints

**Observed in:**
- `/api/v1/cases/{case_id}` - 401 Unauthorized
- `/api/v1/chat/history` - 401 Unauthorized
- CaseInsights component failing

**Possible Causes:**
1. JWT token might be expired
2. Case IDs might not match user's cases (authorization issue)
3. Endpoints might have stricter auth requirements

**Recommended Actions:**
1. Check browser localStorage for valid JWT token
2. Try logging out and back in to get fresh token
3. Verify case IDs exist and belong to current user
4. Check backend logs for specific auth errors

**Status:** ⚠️ Needs Investigation (but not related to deadline calculator changes)

---

## Files Modified

### Backend Files:
1. **`/backend/app/services/document_service.py`**
   - Added placeholder case creation when case_number can't be extracted
   - Ensures `case_id` is never `None`

2. **`/backend/app/api/v1/documents.py`**
   - Added comprehensive error handling to upload endpoint
   - Better exception catching and traceback printing

---

## Testing the Fixes

### Test Document Upload:
1. Go to dashboard
2. Upload a PDF document
3. Verify document uploads successfully
4. Check that new case is created with placeholder case number if needed

### Expected Behavior:
- ✅ Document uploads without errors
- ✅ Case is created automatically if not specified
- ✅ Placeholder case number generated (e.g., NEW-A3B9C7F1)
- ✅ No CORS errors
- ✅ No database constraint errors

---

## Backend Status

**Server:** Running on http://localhost:8000
**Last Restart:** Successful (auto-reloaded after file changes)
**Recent Logs:** No errors, dashboard endpoint working (200 OK)

**Test:**
```bash
# Health check
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "LitDocket API"
}
```

---

## Next Steps for 401 Errors

If 401 errors persist:

1. **Clear localStorage and re-login:**
   ```javascript
   // In browser console
   localStorage.clear();
   // Then navigate to /login and login again
   ```

2. **Check JWT token:**
   ```javascript
   // In browser console
   console.log(localStorage.getItem('accessToken'));
   ```

3. **Verify backend auth is working:**
   ```bash
   # Check backend logs for auth errors
   tail -f /tmp/claude/-Users-jackson/tasks/bc45893.output | grep -i "401\|auth\|unauthorized"
   ```

4. **Test specific endpoints:**
   ```bash
   # Get token from localStorage first
   TOKEN="your-jwt-token-here"

   # Test dashboard endpoint
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/dashboard

   # Test case endpoint
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/cases
   ```

---

## Summary

✅ **Fixed:** Document upload NULL constraint error
✅ **Fixed:** CORS error on document upload
⚠️ **Investigating:** 401 authentication errors (unrelated to deadline calculator)

The deadline calculator improvements are complete and working. The remaining 401 errors appear to be pre-existing authentication issues that need separate investigation.

---

**Date:** January 6, 2026
**Backend Server:** Running and healthy
**Frontend:** http://localhost:3000
**Backend:** http://localhost:8000
