$ProjectRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$RepositoryPathMap = @{}
$mapObject = Get-Content -LiteralPath (Join-Path $ProjectRoot '02_公共资源/项目管理/目录迁移/path_map.json') -Raw | ConvertFrom-Json
foreach ($property in $mapObject.PSObject.Properties) { $RepositoryPathMap[$property.Name] = $property.Value }
function Resolve-RepositoryPath([string]$RelativePath) {
    $rel = $RelativePath.Replace('\','/')
    foreach ($key in ($RepositoryPathMap.Keys | Sort-Object Length -Descending)) {
        if ($rel -eq $key -or $rel.StartsWith($key + '/')) {
            return Join-Path $ProjectRoot ($RepositoryPathMap[$key] + $rel.Substring($key.Length))
        }
    }
    return Join-Path $ProjectRoot $RelativePath
}
