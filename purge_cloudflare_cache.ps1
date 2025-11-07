# Cloudflare Cache Purge Script for LaborLooker
# Purges all cached content to eliminate old consent popup

# ⚠️ FILL IN YOUR CREDENTIALS:
$ZONE_ID = "YOUR_ZONE_ID_HERE"  # Found in Cloudflare Dashboard → laborlooker.com → Overview (right sidebar)
$API_TOKEN = "YOUR_API_TOKEN_HERE"  # Create at: Cloudflare Dashboard → My Profile → API Tokens → Create Token

# Cloudflare API endpoint
$uri = "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache"

# Headers
$headers = @{
    "Authorization" = "Bearer $API_TOKEN"
    "Content-Type" = "application/json"
}

# Purge everything
$body = @{
    purge_everything = $true
} | ConvertTo-Json

Write-Host "🔥 Purging ALL Cloudflare cache for laborlooker.com..." -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $body
    
    if ($response.success) {
        Write-Host "✅ SUCCESS! Cache purged completely." -ForegroundColor Green
        Write-Host "Cache ID: $($response.result.id)" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "🎉 The consent popup should be GONE now!" -ForegroundColor Green
        Write-Host "   1. Hard refresh your browser (Ctrl+F5)" -ForegroundColor White
        Write-Host "   2. Clear mobile browser cache" -ForegroundColor White
        Write-Host "   3. Test in incognito mode first" -ForegroundColor White
    } else {
        Write-Host "❌ FAILED: $($response.errors)" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  • Invalid API Token (needs 'Cache Purge' permission)" -ForegroundColor White
    Write-Host "  • Wrong Zone ID" -ForegroundColor White
    Write-Host "  • Token not activated yet" -ForegroundColor White
}
