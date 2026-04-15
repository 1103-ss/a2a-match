$acl = Get-Acl 'C:\Users\Administrator\.qclaw\workspace\skills\abm-cold-email' -ErrorAction SilentlyContinue
if ($acl) {
    Write-Host "Owner: $($acl.Owner)"
    $acl.Access | ForEach-Object {
        Write-Host "$($_.IdentityReference) : $($_.FileSystemRights) : $($_.AccessControlType)"
    }
} else {
    Write-Host "ACL null"
}
