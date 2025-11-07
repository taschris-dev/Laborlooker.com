# 🔥 Cloudflare Cache Purge Instructions

## The Problem
Cloudflare is caching the **old consent popup page** and serving it even though we deleted all the code. The cached version has this text:
> "Agreement & Comprehensive Consent Framework - Binding Legal Agreement..."

## The Solution - Purge Cloudflare Cache

### Option 1: Manual Dashboard Purge (EASIEST)

1. **Log into Cloudflare Dashboard**
   - Go to: https://dash.cloudflare.com
   - Select your **laborlooker.com** domain

2. **Purge Everything**
   - Click **Caching** in left sidebar
   - Click **Configuration** tab
   - Click **"Purge Everything"** button
   - Confirm the purge

3. **Enable Development Mode (Optional)**
   - Still in **Caching** → **Configuration**
   - Toggle **"Development Mode"** to ON
   - This bypasses cache for 3 hours while testing

4. **Test the Site**
   - Hard refresh (Ctrl+F5 or Cmd+Shift+R)
   - Clear browser cache
   - Test in incognito/private mode

---

### Option 2: API Script (FASTER FOR FUTURE)

#### Step 1: Get Your Cloudflare Credentials

**Zone ID:**
1. Go to Cloudflare Dashboard → **laborlooker.com**
2. Scroll down to **API** section in right sidebar
3. Copy the **Zone ID** (looks like: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`)

**API Token:**
1. Go to Cloudflare Dashboard → Click your profile (top right)
2. Click **My Profile** → **API Tokens** tab
3. Click **"Create Token"**
4. Use **"Edit zone DNS"** template OR create custom with:
   - Permissions: **Zone** → **Cache Purge** → **Purge**
   - Zone Resources: **Include** → **Specific zone** → **laborlooker.com**
5. Click **Continue to summary** → **Create Token**
6. **COPY THE TOKEN** (you won't see it again!)

#### Step 2: Edit the PowerShell Script

1. Open: `purge_cloudflare_cache.ps1`
2. Replace these lines:
   ```powershell
   $ZONE_ID = "YOUR_ZONE_ID_HERE"      # Paste your Zone ID
   $API_TOKEN = "YOUR_API_TOKEN_HERE"  # Paste your API Token
   ```

#### Step 3: Run the Script

```powershell
cd "c:\HEC demo program\referal-engine"
.\purge_cloudflare_cache.ps1
```

You should see:
```
🔥 Purging ALL Cloudflare cache for laborlooker.com...
✅ SUCCESS! Cache purged completely.
🎉 The consent popup should be GONE now!
```

---

### Option 3: Cloudflare API via curl (Command Line)

```powershell
$ZONE_ID = "YOUR_ZONE_ID"
$API_TOKEN = "YOUR_API_TOKEN"

$headers = @{
    "Authorization" = "Bearer $API_TOKEN"
    "Content-Type" = "application/json"
}

$body = '{"purge_everything":true}'

Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" `
    -Method Post `
    -Headers $headers `
    -Body $body
```

---

## After Purging Cache

### Clear Browser Cache Too:

**Desktop:**
1. Chrome/Edge: Ctrl+Shift+Delete → Select "All time" → Clear
2. Or use Incognito mode (Ctrl+Shift+N)

**Mobile:**
1. Settings → Apps → Chrome/Safari → Clear cache & data
2. Or use Private/Incognito mode

### Verify It's Gone:

1. Visit: https://laborlooker.com/
2. Check if consent popup appears
3. If it does, check Railway direct URL: https://laborlookercom-production.up.railway.app/
   - If Railway is clean but custom domain shows popup = Cloudflare cache issue
   - Purge again and wait 2-3 minutes

---

## Current Active Headers (Fighting Cache)

Our Cloudflare Worker now sends these headers:

```
Cache-Control: no-cache, no-store, must-revalidate, max-age=0, s-maxage=0
Clear-Site-Data: "cache", "storage"
X-Consent-Free: true
X-Cache-Bust: [timestamp]
```

These headers tell browsers AND Cloudflare to NEVER cache the page.

---

## Troubleshooting

**Still seeing consent popup after purge?**

1. **Check if it's really purged:**
   ```powershell
   $response = Invoke-WebRequest -Uri "https://laborlooker.com/"
   $response.Headers["CF-Cache-Status"]  # Should be "DYNAMIC" not "HIT"
   ```

2. **Check your browser cache:**
   - Open DevTools (F12) → Network tab
   - Check "Disable cache" checkbox
   - Reload page

3. **Nuclear option:**
   - Enable Cloudflare Development Mode (bypasses ALL caching)
   - Clear ALL browser data
   - Test in fresh incognito window
   - Restart browser completely

4. **Verify it's not in code:**
   ```powershell
   cd "c:\HEC demo program\referal-engine"
   Select-String -Path "templates/*.html" -Pattern "Comprehensive Consent Framework"
   ```
   Should return NO results.

---

## Questions?

If you need help:
1. Share your **Zone ID** (it's not sensitive)
2. Tell me if you created the **API Token**
3. Let me know what error you see

The consent popup is **definitely cached in Cloudflare** since:
- ✅ Railway direct URL = Clean (no popup)
- ❌ Custom domain (laborlooker.com) = Shows popup
- ✅ All code deleted from server
- ✅ Headers sending cache-busting commands

**Purging Cloudflare cache WILL fix this!** 🚀
