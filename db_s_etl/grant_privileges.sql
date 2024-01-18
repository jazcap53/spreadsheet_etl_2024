-- file: db/grant_privileges.sql
-- andrew jarcho
-- 2017-04-06

GRANT SELECT, UPDATE, INSERT, DELETE ON sl_nap, sl_night TO jazcap53;
GRANT USAGE ON sl_night_night_id_seq TO jazcap53;
GRANT USAGE ON sl_nap_nap_id_seq TO jazcap53;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO andy;
