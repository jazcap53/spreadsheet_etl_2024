-- file: db_test/grant_privileges.sql
-- andrew jarcho
-- 2017-04-06

GRANT SELECT, UPDATE, INSERT, DELETE ON slt_nap, slt_night TO jazcap53;
GRANT USAGE ON slt_night_night_id_seq TO jazcap53;
GRANT USAGE ON slt_nap_nap_id_seq TO jazcap53;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO jazcap53;

GRANT SELECT, UPDATE, INSERT, DELETE ON slt_nap, slt_night TO andy;
GRANT USAGE ON slt_night_night_id_seq TO andy;
GRANT USAGE ON slt_nap_nap_id_seq TO andy;
