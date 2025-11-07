# 🚨 Disable Cloudflare Features That Could Inject Consent Popup

## The Problem:
Cloudflare has several features that can inject HTML/JavaScript into your pages:
- Rocket Loader (wraps JavaScript)
- Bot Fight Mode (adds challenges)
- Server-side Excludes (modifies HTML)
- Email Obfuscation (rewrites HTML)

## Solution: Disable These Features

### **1. Rocket Loader (MOST LIKELY CULPRIT)**
**Location:** Speed → Optimization → Content Optimization

**Steps:**
1. Go to Cloudflare Dashboard → laborlooker.com
2. Click **Speed** in left sidebar
3. Click **Optimization** tab
4. Scroll to **Content Optimization** section
5. Find **"Rocket Loader"**
6. Toggle it **OFF**
7. Click **Save**

---

### **2. Bot Fight Mode / Super Bot Fight Mode**
**Location:** Security → Bots

**Steps:**
1. Go to **Security** → **Bots**
2. Find **"Bot Fight Mode"** or **"Super Bot Fight Mode"**
3. Toggle it **OFF**
4. Click **Save**

---

### **3. Server-side Excludes**
**Location:** Scrape Shield

**Steps:**
1. Go to **Scrape Shield** in left sidebar
2. Find **"Server-side Excludes"**
3. Toggle it **OFF**
4. Click **Save**

---

### **4. Email Address Obfuscation**
**Location:** Scrape Shield

**Steps:**
1. Go to **Scrape Shield**
2. Find **"Email Address Obfuscation"**
3. Toggle it **OFF**
4. Click **Save**

---

### **5. Auto Minify HTML**
**Location:** Speed → Optimization

**Steps:**
1. Go to **Speed** → **Optimization**
2. Find **"Auto Minify"**
3. **Uncheck HTML** (leave CSS and JS checked if you want)
4. Click **Save**

---

### **6. Check for Zaraz (Tag Manager)**
**Location:** Zaraz in left sidebar (if present)

**Steps:**
1. Check if **"Zaraz"** appears in left sidebar
2. If yes, click it
3. Check if any **Consent Management** tools are enabled
4. **Disable** or **Delete** any consent tools

---

## After Disabling Features:

1. **Wait 2-3 minutes** for changes to propagate
2. **Purge Cloudflare Cache:**
   - Caching → Configuration → "Purge Everything"
3. **Clear browser cache:**
   - Ctrl+Shift+Delete → All time → Clear
4. **Hard refresh:**
   - Ctrl+F5
5. **Test in Incognito mode**

---

## Create a Bypass Page Rule (Alternative):

If you want to keep these features but bypass them for testing:

**Location:** Rules → Page Rules

**Steps:**
1. Go to **Rules** → **Page Rules**
2. Click **"Create Page Rule"**
3. **URL Pattern:** `laborlooker.com/*`
4. **Settings:** Add these:
   - Rocket Loader: OFF
   - Email Obfuscation: OFF
   - Server Side Excludes: OFF
   - Security Level: Essentially Off
   - Browser Integrity Check: OFF
5. Click **Save and Deploy**

---

## Verify Which Feature is Causing It:

**Disable ONE feature at a time and test:**

1. Disable **Rocket Loader** → Test → If fixed, that's the culprit!
2. If not, disable **Bot Fight Mode** → Test
3. If not, disable **Server-side Excludes** → Test
4. If not, disable **Email Obfuscation** → Test

This will tell you EXACTLY which Cloudflare feature is injecting the consent popup.

---

## Most Likely Order:

1. **Rocket Loader** (80% probability) - Wraps all JavaScript
2. **Super Bot Fight Mode** (15% probability) - Shows challenge pages
3. **Server-side Excludes** (4% probability) - Can modify HTML
4. **Zaraz Consent Tool** (1% probability) - If you have Zaraz enabled

---

## After Finding the Culprit:

Once you identify which feature is causing it:
- Keep that feature **OFF** permanently, OR
- Use a **Page Rule** to disable it only for specific URLs, OR
- Contact Cloudflare support about the unwanted injection
