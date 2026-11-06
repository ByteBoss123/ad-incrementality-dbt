SELECT c.campaign_id, Count(a.ad_id) AS ad_count,
       Sum(a.impressions) AS impressions, Sum(a.clicks) AS clicks,
       Sum(a.spend) AS spend, Sum(a.approved_conversions) AS approved_conversions,
       Sum(a.spend) / IIf(Sum(a.approved_conversions)=0, Null, Sum(a.approved_conversions)) AS cost_per_approved_conversion
FROM Campaigns AS c INNER JOIN Ads AS a ON c.campaign_id=a.campaign_id
GROUP BY c.campaign_id;
