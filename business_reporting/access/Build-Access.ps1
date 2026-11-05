# Requires Windows with Microsoft Access installed. Not executed in this environment.
# Creates a NEW database; refuses to replace an existing file.
param([string]$OutputPath = (Join-Path $PSScriptRoot 'CampaignReporting.accdb'))
$ErrorActionPreference = 'Stop'
if (Test-Path $OutputPath) { throw 'Output already exists. Choose a new path.' }
$csvPath = Join-Path $PSScriptRoot '../../raw/KAG_conversion_data.csv'
$rows = Import-Csv $csvPath
$access = $null
$db = $null
try {
    $access = New-Object -ComObject Access.Application
    $access.NewCurrentDatabase([IO.Path]::GetFullPath($OutputPath))
    $db = $access.CurrentDb()
    $ddl = Get-Content (Join-Path $PSScriptRoot 'schema.sql') -Raw
    foreach ($statement in ($ddl -split ';')) {
        if ($statement.Trim()) { $db.Execute($statement, 128) }
    }
    $campaignInsert = $db.CreateQueryDef('', 'PARAMETERS p TEXT(32); INSERT INTO Campaigns (campaign_id) VALUES (p)')
    foreach ($campaign in ($rows.xyz_campaign_id | Sort-Object -Unique)) {
        $campaignInsert.Parameters.Item('p').Value = [string]$campaign
        $campaignInsert.Execute(128)
    }
    $insert = $db.CreateQueryDef('', 'PARAMETERS p0 TEXT(32), p1 TEXT(32), p2 TEXT(32), p3 TEXT(16), p4 TEXT(8), p5 LONG, p6 LONG, p7 LONG, p8 DOUBLE, p9 LONG, p10 LONG; INSERT INTO Ads VALUES (p0,p1,p2,p3,p4,p5,p6,p7,p8,p9,p10)')
    foreach ($row in $rows) {
        $values = @([string]$row.ad_id, [string]$row.xyz_campaign_id, [string]$row.fb_campaign_id,
            [string]$row.age, [string]$row.gender, [int]$row.interest, [int]$row.Impressions,
            [int]$row.Clicks, [double]::Parse($row.Spent, [Globalization.CultureInfo]::InvariantCulture),
            [int]$row.Total_Conversion, [int]$row.Approved_Conversion)
        for ($i=0; $i -lt $values.Count; $i++) { $insert.Parameters.Item("p$i").Value = $values[$i] }
        $insert.Execute(128)
    }
    $query = Get-Content (Join-Path $PSScriptRoot 'campaign_totals.sql') -Raw
    $null = $db.CreateQueryDef('CampaignTotals', $query)
    $check = $db.OpenRecordset('SELECT Count(*) AS n FROM Ads')
    if ($check.Fields.Item('n').Value -ne $rows.Count) { throw 'Import count mismatch' }
    $check.Close()
    Write-Output "Created $OutputPath with $($rows.Count) ads. Open CampaignTotals and compare validation.json."
} finally {
    if ($null -ne $db) { $db.Close() }
    if ($null -ne $access) { $access.Quit() }
}
