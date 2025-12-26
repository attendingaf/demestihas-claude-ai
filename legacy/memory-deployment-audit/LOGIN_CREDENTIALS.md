# DemestiChat Login Credentials Guide
**Date**: 2025-11-15

---

## Authentication System Overview

### Login Mechanism Type
**Backend API Authentication** (Database-backed)

- **Type**: PostgreSQL database with hashed passwords
- **Endpoints**: 
  - `/auth/login` - Username/password authentication
  - `/auth/register` - New user registration
  - `/auth/token` - Insecure token generation (deprecated)
- **Method**: JWT Bearer tokens (1 hour expiry)
- **Storage**: PostgreSQL database (users table)

---

## Current Status

### Existing Users
Based on backend logs and testing:
- **User `testuser`** exists in the database
- **User `mene`** may exist but password is unknown
- Passwords are hashed (cannot be retrieved)

### Login Attempts
❌ `mene` / `test123` - Failed (Invalid credentials)
❌ Direct database access - Failed (role permissions)

---

## How to Create/Register an Account

### Option 1: Via Streamlit UI (Recommended)

1. **Access**: http://178.156.170.161:8501
2. **Click**: "Register" tab on login page
3. **Fill in**:
   - Username: Choose unique username (e.g., `mene`, `cindy`, `persephone`)
   - Display Name: Your full name
   - Email: Optional (for future password recovery)
   - Password: Minimum 6 characters
   - Confirm Password: Re-enter password
4. **Click**: "Create Account"
5. **Result**: Account created, switch to "Login" tab and sign in

### Option 2: Via API (Direct)

```bash
# Register new user
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "mene",
    "password": "YourSecurePassword123",
    "display_name": "Mene",
    "email": "mene@family.com",
    "role": "family"
  }'

# Login with credentials
curl -X POST "http://localhost:8000/auth/login?user_id=mene&password=YourSecurePassword123"
```

---

## Recommended User Accounts

### Primary User (Mene)
```
Username: mene
Password: [Choose secure password]
Display Name: Mene
Email: [Optional]
Role: family
```

### Family Members
```
Username: cindy
Password: [Choose secure password]
Display Name: Cindy
Role: family
```

```
Username: persephone
Password: [Choose secure password]
Display Name: Persephone
Role: family
```

```
Username: stylianos
Password: [Choose secure password]
Display Name: Stylianos
Role: family
```

```
Username: francisca
Password: [Choose secure password]
Display Name: Francisca
Role: family
```

---

## Password Requirements

- **Minimum Length**: 6 characters
- **Recommended**: 12+ characters with mix of:
  - Uppercase letters
  - Lowercase letters
  - Numbers
  - Special characters
- **Storage**: Hashed in PostgreSQL (bcrypt/similar)

---

## Security Features

✅ **Encrypted Passwords**: Stored as hashes (not plaintext)
✅ **JWT Tokens**: 1-hour expiry with automatic refresh
✅ **Session Management**: Secure session state
✅ **Role-Based Access**: Family role for standard access
🔒 **Private Data**: Each user has isolated memories

---

## Quick Setup Steps

### For Mene (Primary User)

1. Open http://178.156.170.161:8501
2. Click "Register" tab
3. Create account:
   ```
   Username: mene
   Display Name: Mene
   Password: [Create strong password]
   ```
4. Click "Create Account"
5. Switch to "Login" tab
6. Sign in with your credentials

### Verification

After login, you should see:
- ✅ Welcome message with display name
- ✅ User profile in sidebar
- ✅ Access to all chat features
- ✅ Access to Memory System
- ✅ Logout button available

---

## Troubleshooting

### "Invalid username or password"
- **Cause**: Wrong credentials or account doesn't exist
- **Solution**: Create account via Register tab first

### "User ID already exists"
- **Cause**: Username already taken
- **Solution**: Choose different username or login with existing credentials

### "Login request timed out"
- **Cause**: Backend service slow/down
- **Solution**: Wait a moment and try again

### Cannot access UI
- **Cause**: Container might be down
- **Check**: `docker ps | grep streamlit`
- **Restart**: `docker restart demestihas-streamlit`

---

## Backend API Endpoints

### Authentication
- **POST** `/auth/register` - Create new account
- **POST** `/auth/login` - Login with password
- **POST** `/auth/token` - Get token (insecure, use login instead)

### Parameters
```
Login/Register:
- user_id: string (username)
- password: string (hashed on backend)
- display_name: string (optional for login)
- email: string (optional)
- role: string (default: "family")
```

---

## Current Known Users

Based on testing:
- `testuser` - Exists in database (password unknown)
- `mene` - May exist, password unknown

**Recommendation**: Create fresh account via UI registration.

---

## Security Notes

⚠️ **Important**:
- The `/auth/token` endpoint is INSECURE (no password required)
- Use `/auth/login` for production
- Backend logs show warnings about insecure token generation
- Always use strong passwords
- JWT tokens expire after 1 hour (auto-refresh in memory_service)

---

## Next Steps

1. **Create Account**: Use Streamlit UI registration
2. **Login**: Sign in with new credentials  
3. **Test Memory System**: Create/search memories
4. **Add Family Members**: Register additional accounts

---

**Access URL**: http://178.156.170.161:8501

**Documentation**: /root/memory-deployment-audit/LOGIN_CREDENTIALS.md
