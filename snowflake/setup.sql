-- Run once in a Snowsight worksheet (trial account, ACCOUNTADMIN).
create database if not exists RAW;
create schema if not exists RAW.CRITEO;
create schema if not exists RAW.ADS;
create database if not exists ANALYTICS;

-- After connecting Sigma through Partner Connect (Admin > Partner Connect > Sigma),
-- Snowflake creates PC_SIGMA_ROLE. Let Sigma read the dbt marts:
-- grant usage on database ANALYTICS to role PC_SIGMA_ROLE;
-- grant usage on all schemas in database ANALYTICS to role PC_SIGMA_ROLE;
-- grant select on all tables in database ANALYTICS to role PC_SIGMA_ROLE;
-- grant select on future tables in database ANALYTICS to role PC_SIGMA_ROLE;

-- dbt/loader service user (key pair). Reuses the same public key as SIGMA_SVC.
create role if not exists DBT_ROLE;
grant usage on warehouse COMPUTE_WH to role DBT_ROLE;
grant all on database RAW to role DBT_ROLE;
grant all on all schemas in database RAW to role DBT_ROLE;
grant all on database ANALYTICS to role DBT_ROLE;
grant role DBT_ROLE to role ACCOUNTADMIN;
create user if not exists DBT_SVC type = service default_role = DBT_ROLE default_warehouse = COMPUTE_WH;
grant role DBT_ROLE to user DBT_SVC;
-- alter user DBT_SVC set rsa_public_key = '<same public key as SIGMA_SVC>';
