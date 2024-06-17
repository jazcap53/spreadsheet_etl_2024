-- file: db_s_etl/create_tables.sql
-- andrew jarcho
-- 2017-02-16

-- Set psql to stop on first error
\set ON_ERROR_STOP on

-- Check if connected to the correct database
DO $$
BEGIN
    IF current_database() != 'sleep' THEN
        RAISE EXCEPTION 'You are not connected to the production database (sleep). Aborting script.';
    END IF;
END $$;

-- If connected to the correct database, proceed with table creation
DROP TABLE IF EXISTS sl_night CASCADE;

CREATE TABLE sl_night (
    night_id SERIAL UNIQUE,
    start_date date NOT NULL,
    start_time time NOT NULL,
    start_no_data boolean,
    end_no_data boolean,
    PRIMARY KEY (night_id),
    CHECK (start_no_data IS FALSE OR end_no_data IS FALSE)
);

DROP TABLE IF EXISTS sl_nap;

CREATE TABLE sl_nap (
    nap_id SERIAL UNIQUE,
    start_time time NOT NULL,
    duration interval hour to minute NOT NULL,
    night_id integer NOT NULL,
    PRIMARY KEY (nap_id),
    FOREIGN KEY (night_id) REFERENCES sl_night (night_id)
);

-- Reset ON_ERROR_STOP
\set ON_ERROR_STOP off