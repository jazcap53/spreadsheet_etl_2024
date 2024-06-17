-- file: db_s_etl/grant_privileges.sql
-- andrew jarcho
-- 2017-04-06

\set ON_ERROR_STOP on

DO $$
   BEGIN
     IF NOT current_database() = 'sleep' THEN
       RAISE EXCEPTION 'You are not connected to the production database (sleep). Aborting script.';
     END IF;
   END $$;


GRANT SELECT, UPDATE, INSERT, DELETE ON sl_nap, sl_night TO jazcap53;
GRANT USAGE ON sl_night_night_id_seq TO jazcap53;
GRANT USAGE ON sl_nap_nap_id_seq TO jazcap53;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO andy;

\set ON_ERROR_STOP off
