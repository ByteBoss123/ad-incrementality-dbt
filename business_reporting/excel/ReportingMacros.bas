Attribute VB_Name = "ReportingMacros"
Option Explicit

' Import this module into a COPY of campaign_reporting.xlsx and save as .xlsm.
' Native Excel execution is required. This module has not been executed in Excel.
Public Sub BuildCampaignPivot()
    Dim wb As Workbook, source As ListObject, target As Worksheet
    Dim cache As PivotCache, pivot As PivotTable
    Set wb = ThisWorkbook
    Set source = wb.Worksheets("Ads").ListObjects("AdsTable")
    On Error Resume Next
    Set target = wb.Worksheets("Campaign Pivot")
    On Error GoTo 0
    If Not target Is Nothing Then
        MsgBox "Campaign Pivot already exists. Run RefreshReport instead."
        Exit Sub
    End If
    Set target = wb.Worksheets.Add(After:=wb.Worksheets("Campaigns"))
    target.Name = "Campaign Pivot"
    target.Range("A1").Value = "Campaign totals by age band"
    Set cache = wb.PivotCaches.Create(SourceType:=xlDatabase, SourceData:=source.Name)
    Set pivot = cache.CreatePivotTable(TableDestination:=target.Range("A3"), TableName:="CampaignByAge")
    With pivot
        .PivotFields("xyz_campaign_id").Orientation = xlRowField
        .PivotFields("age").Orientation = xlRowField
        .PivotFields("gender").Orientation = xlPageField
        .AddDataField .PivotFields("Spent"), "Total spend", xlSum
        .AddDataField .PivotFields("Approved_Conversion"), "Approved conversions", xlSum
        .AddDataField .PivotFields("Clicks"), "Total clicks", xlSum
        .AddDataField .PivotFields("Impressions"), "Total impressions", xlSum
        .DataFields("Total spend").NumberFormat = "#,##0.00"
        .RowAxisLayout xlTabularRow
    End With
    target.Columns.AutoFit
End Sub

Public Sub RefreshReport()
    Dim ws As Worksheet, pt As PivotTable
    On Error GoTo Failed
    Application.ScreenUpdating = False
    ThisWorkbook.RefreshAll
    Application.CalculateUntilAsyncQueriesDone
    For Each ws In ThisWorkbook.Worksheets
        For Each pt In ws.PivotTables
            pt.RefreshTable
        Next pt
    Next ws
    Application.CalculateFull
    Application.ScreenUpdating = True
    MsgBox "Refresh completed. Reconcile totals with validation.json before distribution."
    Exit Sub
Failed:
    Application.ScreenUpdating = True
    MsgBox "Refresh failed: " & Err.Description, vbExclamation
End Sub
