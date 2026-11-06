# Campaign performance review

Scope: the repository's existing 1,143-ad export across three campaigns. No dates, budgets, revenue or confirmed currency code are available. Monetary amounts below use source units. This is a historical portfolio analysis, not Sony data.

| Campaign | Spend | Approved conversions | Cost per approved conversion |
|---|---:|---:|---:|
| 916 | 149.71 | 24 | 6.24 |
| 936 | 2,893.37 | 183 | 15.81 |
| 1178 | 55,662.15 | 872 | 63.83 |
| Total | 58,705.23 | 1,079 | 54.41 |

Campaign 1178 accounts for approximately 94.8% of spend and has the highest observed CPA. Prioritize its conversion tracking and audience/creative review because it has the largest absolute spend exposure.

Campaign 916 has the lowest observed CPA but only 24 approved conversions and about 0.3% of spend. Its efficiency does not establish that a large budget transfer would preserve the same performance. Design a limited, randomized budget test before making a scaling recommendation.

Keep routine reporting focused on spend, impressions, clicks and approved conversions. Request dates, revenue, margin, approved targets and attribution definitions before adding pacing, ROAS or profitability decisions. CPA here is cost per approved conversion; it is not proven customer acquisition cost.

All totals reconcile to the checked-in CSV through independent Python/SQLite calculations. Cross-campaign comparisons are descriptive; causal claims belong to the separate randomized experiment analysis.
