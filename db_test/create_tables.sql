-- file: db_test/create_tables.sql
-- andrew jarcho
-- 2017-08-12

DROP TABLE IF EXISTS slt_night CASCADE;

CREATE TABLE slt_night (
    night_id SERIAL UNIQUE,
    start_date date NOT NULL,
    start_time time NOT NULL,
    PRIMARY KEY (night_id)
);


DROP TABLE IF EXISTS slt_nap;

CREATE TABLE slt_nap (
    nap_id SERIAL UNIQUE, 
    start_time time NOT NULL,
    duration interval NOT NULL,
    night_id integer NOT NULL,
    PRIMARY KEY (nap_id),
    FOREIGN KEY (night_id) REFERENCES slt_night (night_id)
);
