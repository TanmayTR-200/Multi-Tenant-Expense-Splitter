# End-to-end smoke test: register -> group -> members -> expenses -> settle
$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:8000/api'
$settle = 'http://127.0.0.1:8001'

function PostJson($url, $body, $token) {
    $h = @{ 'Content-Type' = 'application/json' }
    if ($token) { $h['Authorization'] = "Bearer $token" }
    try {
        return Invoke-RestMethod -Uri $url -Method Post -Headers $h -Body ($body | ConvertTo-Json -Depth 5)
    } catch {
        $resp = $_.Exception.Response
        if ($resp) {
            $sr = New-Object IO.StreamReader($resp.GetResponseStream())
            throw "POST $url -> $([int]$resp.StatusCode) $($sr.ReadToEnd())"
        }
        throw
    }
}
function GetJson($url, $token) {
    $h = @{}
    if ($token) { $h['Authorization'] = "Bearer $token" }
    try {
        return Invoke-RestMethod -Uri $url -Method Get -Headers $h
    } catch {
        $resp = $_.Exception.Response
        if ($resp) {
            $sr = New-Object IO.StreamReader($resp.GetResponseStream())
            throw "GET $url -> $([int]$resp.StatusCode) $($sr.ReadToEnd())"
        }
        throw
    }
}

$suffix = Get-Random
$alice = PostJson "$base/auth/register/" @{ username = "alice$suffix"; email = "a$suffix@x.com"; password = 'password123' }
$bob   = PostJson "$base/auth/register/" @{ username = "bob$suffix";   email = "b$suffix@x.com"; password = 'password123' }
$mallory = PostJson "$base/auth/register/" @{ username = "mal$suffix"; email = "m$suffix@x.com"; password = 'password123' }
Write-Host "1. registered alice/bob/mallory"

# Login also works (JWT endpoint)
$login = PostJson "$base/auth/login/" @{ username = "alice$suffix"; password = 'password123' }
Write-Host "2. login ok: $(($login.access -ne $null))"

$ta = $alice.access; $tb = $bob.access; $tm = $mallory.access
$aid = $null
# user id from token payload
function UserIdFromToken($t) {
    $p = $t.Split('.')[1].Replace('-', '+').Replace('_', '/')
    switch ($p.Length % 4) { 2 { $p += '==' } 3 { $p += '=' } }
    return ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($p)) | ConvertFrom-Json).user_id
}
$aliceId = UserIdFromToken $ta; $bobId = UserIdFromToken $tb

$group = PostJson "$base/groups/" @{ name = 'Ski Trip' } $ta
$gid = $group.id
Write-Host "3. created group $gid"

$null = PostJson "$base/groups/$gid/members/" @{ username = "bob$suffix" } $ta
Write-Host "4. added bob to group"

# TENANT ISOLATION: mallory must not see or touch the group
try { $null = GetJson "$base/groups/$gid/" $tm; Write-Host "5a. FAIL mallory saw the group!" }
catch { Write-Host "5a. mallory blocked from group detail (expected)" }
try { $null = PostJson "$base/groups/$gid/" @{ description='hack'; amount_cents=1 } $tm; Write-Host "5b. FAIL mallory added an expense!" }
catch { Write-Host "5b. mallory blocked from adding expense (expected)" }
try { $null = GetJson "$base/groups/$gid/" $null; Write-Host "5c. FAIL unauthenticated access!" }
catch { Write-Host "5c. unauthenticated blocked (expected)" }

# Expenses: alice pays 100.03, bob pays 50.00 -> equal splits among members
$null = PostJson "$base/groups/$gid/" @{ description = 'Cabin'; amount_cents = 10003 } $ta
$null = PostJson "$base/groups/$gid/" @{ description = 'Groceries'; amount_cents = 5000 } $tb
Write-Host "6. added two expenses"

$detail = GetJson "$base/groups/$gid/" $ta
$detail.balances | ForEach-Object { Write-Host ("   balance {0}: {1} cents" -f $_.username, $_.balance_cents) }

# SETTLEMENT via FastAPI
$s = PostJson "$settle/settle" @{ group_id = $gid } $ta
Write-Host "7. settlement for group '$($s.group_name)':"
$s.transfers | ForEach-Object { Write-Host ("   {0} pays {1}: {2} cents" -f $_.from.username, $_.to.username, $_.amount_cents) }

# settle with non-member token -> must 404
try { $null = PostJson "$settle/settle" @{ group_id = $gid } $tm; Write-Host "8. FAIL mallory got settlement!" }
catch { Write-Host "8. mallory blocked from settlement (expected)" }

# settle without token -> 401
try { $null = PostJson "$settle/settle" @{ group_id = $gid } $null; Write-Host "9. FAIL no-token allowed!" }
catch { Write-Host "9. no-token blocked (expected)" }
Write-Host "SMOKE TEST COMPLETE"
