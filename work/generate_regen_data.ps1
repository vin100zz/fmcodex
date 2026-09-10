$ErrorActionPreference = 'Stop'

$sourcePath = Join-Path $PSScriptRoot '..\data\players.csv'
$targetPath = Join-Path $PSScriptRoot '..\data\regens'
$players = Import-Csv -Path $sourcePath -Delimiter ';' -Encoding Ansi

$countries = @(
    [pscustomobject]@{ source = 'France'; code = 'FRA' },
    [pscustomobject]@{ source = 'Espagne'; code = 'ESP' },
    [pscustomobject]@{ source = 'Italie'; code = 'ITA' },
    [pscustomobject]@{ source = 'Angleterre'; code = 'ENG' },
    [pscustomobject]@{ source = 'Allemagne'; code = 'GER' }
)

New-Item -ItemType Directory -Force -Path $targetPath | Out-Null
$rows = foreach ($country in $countries) {
    $matches = @($players | Where-Object { ($_.Nation -split ' / ') -contains $country.source })
    $names = foreach ($player in $matches) {
        $parts = $player.Name -split ',', 2
        [pscustomobject]@{
            first_name = if ($parts.Count -gt 1) { $parts[1].Trim() } else { $parts[0].Trim() }
            last_name = $parts[0].Trim()
        }
    }
    $names | Group-Object first_name | ForEach-Object {
        [pscustomobject]@{ name = $_.Name; weight = $_.Count }
    } | Sort-Object name | Export-Csv -Path (Join-Path $targetPath "prenoms_$($country.code).csv") -Delimiter ';' -Encoding utf8BOM -NoTypeInformation
    $names | Group-Object last_name | ForEach-Object {
        [pscustomobject]@{ name = $_.Name; weight = $_.Count }
    } | Sort-Object name | Export-Csv -Path (Join-Path $targetPath "noms_$($country.code).csv") -Delimiter ';' -Encoding utf8BOM -NoTypeInformation
    $meanValue = ($matches | ForEach-Object { [int64]$_.Value } | Measure-Object -Average).Average
    [pscustomobject]@{
        code_iso3 = $country.code
        nom_source = $country.source
        poids_production = $matches.Count
        force_football = [math]::Round([math]::Min(100, 20 + 4 * [math]::Log10([math]::Max(1, $meanValue))))
    }
}
$rows | Export-Csv -Path (Join-Path $targetPath 'nations.csv') -Delimiter ';' -Encoding utf8BOM -NoTypeInformation
