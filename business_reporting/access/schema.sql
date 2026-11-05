CREATE TABLE Campaigns (campaign_id TEXT(32) CONSTRAINT PK_Campaigns PRIMARY KEY);
CREATE TABLE Ads (ad_id TEXT(32) CONSTRAINT PK_Ads PRIMARY KEY, campaign_id TEXT(32) NOT NULL, fb_campaign_id TEXT(32), age_band TEXT(16), gender TEXT(8), interest LONG, impressions LONG, clicks LONG, spend DOUBLE, total_conversions LONG, approved_conversions LONG);
ALTER TABLE Ads ADD CONSTRAINT FK_Ads_Campaign FOREIGN KEY (campaign_id) REFERENCES Campaigns (campaign_id);
