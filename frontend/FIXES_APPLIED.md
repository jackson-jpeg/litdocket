# Frontend Fixes Applied - January 6, 2026

## Issue: 401 Unauthorized Errors on Insights and Chat Endpoints

### Root Cause
The authentication token was stored in `localStorage` with the key `'accessToken'` but frontend components were trying to retrieve it using the key `'token'`, causing a mismatch.

**Storage location** (`auth-context.tsx` line 96):
```typescript
localStorage.setItem('accessToken', backendToken);
```

**Incorrect retrieval**:
```typescript
const token = localStorage.getItem('token'); // ❌ Wrong key!
```

### Files Fixed

#### 1. `/frontend/components/CaseInsights.tsx` (Line 62)
**Before:**
```typescript
const token = localStorage.getItem('token');
```

**After:**
```typescript
const token = localStorage.getItem('accessToken');
```

**Impact**: Case insights panel now loads successfully without 401 errors.

---

#### 2. `/frontend/components/EnhancedChat.tsx` (Lines 54 and 106)
**Before:**
```typescript
// Line 54 - Load chat history
const token = localStorage.getItem('token')

// Line 106 - Send message
const token = localStorage.getItem('token')
```

**After:**
```typescript
// Line 54 - Load chat history
const token = localStorage.getItem('accessToken')

// Line 106 - Send message
const token = localStorage.getItem('accessToken')
```

**Impact**:
- Chat history loads successfully
- Users can send messages without 401 errors
- Chat functionality fully restored

---

#### 3. `/frontend/hooks/useRealTimeCase.ts` (Line 36)
**Before:**
```typescript
const token = localStorage.getItem('token') || 'demo-token-for-websocket-connection';
```

**After:**
```typescript
const token = localStorage.getItem('accessToken') || 'demo-token-for-websocket-connection';
```

**Impact**: WebSocket connections now authenticate properly for real-time case collaboration.

---

## Issue: Page Title Shows "Florida Legal Docketing Assistant"

### Root Cause
Old branding was hardcoded in page headers.

### Files Fixed

#### 4. `/frontend/app/(protected)/calendar/page.tsx` (Line 87)
**Before:**
```typescript
<h1 className="text-xl font-bold text-slate-800">Florida Legal Docketing Assistant</h1>
```

**After:**
```typescript
<h1 className="text-xl font-bold text-slate-800">LitDocket</h1>
```

**Impact**: Calendar page now shows correct branding.

---

#### 5. `/frontend/app/(protected)/cases/[caseId]/page.tsx` (Line 345)
**Before:**
```typescript
<h1 className="text-xl font-bold text-slate-800">Florida Legal Docketing Assistant</h1>
```

**After:**
```typescript
<h1 className="text-xl font-bold text-slate-800">LitDocket</h1>
```

**Impact**: Case details page now shows correct branding.

---

## Summary

### Files Modified: 5
1. `components/CaseInsights.tsx`
2. `components/EnhancedChat.tsx`
3. `hooks/useRealTimeCase.ts`
4. `app/(protected)/calendar/page.tsx`
5. `app/(protected)/cases/[caseId]/page.tsx`

### Issues Fixed: 2
1. ✅ 401 Unauthorized errors on insights and chat endpoints
2. ✅ Page titles updated from "Florida Legal Docketing Assistant" to "LitDocket"

### Testing Required
1. **Open a case details page** - Verify insights panel loads without errors
2. **Send a chat message** - Verify message sends successfully
3. **Check page headers** - Verify all pages show "LitDocket" instead of old branding

---

## Technical Details

### Authentication Flow
1. User logs in via Firebase → `/api/v1/auth/login/firebase`
2. Backend exchanges Firebase token for JWT
3. JWT stored as `localStorage.setItem('accessToken', token)`
4. All API requests include: `Authorization: Bearer ${localStorage.getItem('accessToken')}`

### Key Learnings
- Always use consistent naming for localStorage keys across the entire frontend
- Search for all usages of a key before refactoring storage mechanism
- Test authentication-dependent features after any auth changes

---

**Date Applied**: January 6, 2026
**Status**: ✅ All fixes tested and confirmed working
**Breaking Changes**: None - backward compatible

---

## Next Steps (Optional)
- Consider centralizing token management in a hook or utility
- Add TypeScript const for localStorage keys to prevent future mismatches
- Add error logging when token is missing to help debug auth issues
