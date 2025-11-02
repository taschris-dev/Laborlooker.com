# Clean up script to remove irrelevant files and organize the project structure
# This will keep the modern-deployment folder and essential legacy files for reference

# Files and folders to keep (core Flask app and modern deployment)
$keepItems = @(
    "modern-deployment",
    ".git",
    ".gitignore",
    ".env",
    "main.py",
    "requirements.txt",
    "static",
    "templates",
    "instance",
    "config",
    ".venv",
    "__pycache__",
    "cleanup.ps1"
)

# Get current directory
$currentDir = Get-Location

Write-Host "Starting cleanup of legacy deployment files..." -ForegroundColor Yellow
Write-Host "Current directory: $currentDir" -ForegroundColor Blue

# Get all items in current directory
$allItems = Get-ChildItem -Force

$itemsToDelete = @()
$itemsToKeep = @()

foreach ($item in $allItems) {
    if ($keepItems -contains $item.Name) {
        $itemsToKeep += $item.Name
    } else {
        $itemsToDelete += $item.Name
    }
}

Write-Host ""
Write-Host "Analysis Results:" -ForegroundColor Green
Write-Host "Items to keep ($($itemsToKeep.Count)):" -ForegroundColor Green
foreach ($item in $itemsToKeep) {
    Write-Host "   - $item" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Items to delete ($($itemsToDelete.Count)):" -ForegroundColor Red
foreach ($item in $itemsToDelete) {
    Write-Host "   - $item" -ForegroundColor Gray
}

# Ask for confirmation
Write-Host ""
Write-Host "This will permanently delete $($itemsToDelete.Count) files/folders." -ForegroundColor Yellow
$confirmation = Read-Host "Do you want to proceed? (y/N)"

if ($confirmation -eq 'y' -or $confirmation -eq 'Y') {
    Write-Host ""
    Write-Host "Deleting legacy files..." -ForegroundColor Yellow
    
    $deleteCount = 0
    foreach ($itemName in $itemsToDelete) {
        try {
            $itemPath = Join-Path $currentDir $itemName
            if (Test-Path $itemPath) {
                Remove-Item $itemPath -Recurse -Force
                Write-Host "   Deleted: $itemName" -ForegroundColor Green
                $deleteCount++
            }
        } catch {
            Write-Host "   Failed to delete: $itemName - $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    Write-Host "Cleanup complete!" -ForegroundColor Green
    Write-Host "   - Deleted: $deleteCount items" -ForegroundColor Gray
    Write-Host "   - Kept: $($itemsToKeep.Count) items" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Your project now contains:" -ForegroundColor Blue
    Write-Host "   modern-deployment/ - New cloud-native architecture" -ForegroundColor Cyan
    Write-Host "   Flask app files - Legacy reference (main.py, templates/, static/)" -ForegroundColor Cyan
    Write-Host "   Configuration - Essential config files" -ForegroundColor Cyan
    
} else {
    Write-Host ""
    Write-Host "Cleanup cancelled. No files were deleted." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Blue
Write-Host "   1. cd modern-deployment" -ForegroundColor Gray
Write-Host "   2. pnpm install" -ForegroundColor Gray
Write-Host "   3. Follow DEPLOYMENT_GUIDE.md for setup" -ForegroundColor Gray