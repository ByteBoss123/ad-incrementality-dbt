-- Headline lift mart must account for exactly the users and outcomes in the
-- de-duplicated user table.
with u as (
    select count(*) n, sum(visit) v, sum(conversion) c from {{ ref('int_criteo__users') }}
),
l as (
    select
        sum(case when outcome = 'visit' then t_users + c_users end) n,
        sum(case when outcome = 'visit' then t_conv + c_conv end) v,
        sum(case when outcome = 'conversion' then t_conv + c_conv end) c
    from {{ ref('fct_campaign_lift') }}
)
select * from u cross join l where u.n <> l.n or u.v <> l.v or u.c <> l.c
