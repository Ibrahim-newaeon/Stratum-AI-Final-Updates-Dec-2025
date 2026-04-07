# Test CMS admin pages API
$body = @{email='cms-admin@stratum.ai'; password='StratumCMS2024!'} | ConvertTo-Json
$login = Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/auth/login' -Method Post -Body $body -ContentType 'application/json' -UseBasicParsing
$loginData = $login.Content | ConvertFrom-Json
$token = $loginData.data.access_token
Write-Host "Login success: $($loginData.success)"
Write-Host "Token prefix: $($token.Substring(0, 20))..."

$headers = @{Authorization="Bearer $token"}
try {
    $pages = Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/cms/admin/pages' -Method Get -Headers $headers -UseBasicParsing
    Write-Host "`nAdmin Pages Response:"
    Write-Host $pages.Content.Substring(0, 500)
} catch {
    Write-Host "`nAdmin Pages Error:"
    Write-Host $_.ErrorDetails.Message
    Write-Host $_.Exception.Response.StatusCode
}
