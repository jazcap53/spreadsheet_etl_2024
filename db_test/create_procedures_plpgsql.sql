-- file: db/create_procedures.sql
-- andrew jarcho
-- 2017-04-05


DO $$
   BEGIN
     IF NOT current_database() = 'sleep_test' THEN
       RAISE EXCEPTION 'You are not connected to the test database (sleep_test). Aborting script.';
     END IF;
   END $$;


CREATE OR REPLACE FUNCTION sl_insert_night(
    new_start_date text,
    new_start_time text,
    new_start_no_data boolean,
    new_end_no_data boolean
) RETURNS text AS $$
BEGIN
    INSERT INTO sl_night (night_id, start_date, start_time, start_no_data, end_no_data)
    VALUES (
        nextval('sl_night_night_id_seq'),
        new_start_date::date,
        new_start_time::time without time zone,
        new_start_no_data,
        new_end_no_data
    );
    RETURN 'sl_insert_night() succeeded';
EXCEPTION
    WHEN OTHERS THEN
        RETURN 'error inserting night into db';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION sl_insert_nap(
    new_start_time text,
    new_duration text
) RETURNS text AS $$
DECLARE
    fk_night_id INTEGER;
BEGIN
    SELECT currval('sl_night_night_id_seq') INTO fk_night_id;

    INSERT INTO sl_nap (nap_id, start_time, duration, night_id)
    VALUES (
        nextval('sl_nap_nap_id_seq'),
        new_start_time::time without time zone,
        new_duration::interval,
        fk_night_id
    );
    RETURN 'sl_insert_nap() succeeded';
EXCEPTION
    WHEN OTHERS THEN
        RETURN 'error inserting nap into db';
END;
$$ LANGUAGE plpgsql;