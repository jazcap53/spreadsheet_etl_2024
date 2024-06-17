-- file: db_test/grant_privileges.sql
-- andrew jarcho
-- 2017-04-06

\set ON_ERROR_STOP on

-- Check if connected to the correct database
DO $$
BEGIN
    IF current_database() != 'sleep_test' THEN
        RAISE EXCEPTION 'You are not connected to the test database (sleep_test). Aborting script.';
    END IF;
END $$;

GRANT SELECT, UPDATE, INSERT, DELETE ON sl_nap, sl_night TO andyat;
GRANT USAGE ON sl_night_night_id_seq TO andyat;
GRANT USAGE ON sl_nap_nap_id_seq TO andyat;


\set ON_ERROR_STOP off