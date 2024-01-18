-- file: db/create_procedures.sql
-- andrew jarcho
-- 2017-04-05


-- the below are modeled on the last example at 
-- https://www.postgresql.org/docs/9.3/static/plpython-database.html

DROP FUNCTION sl_insert_night(date, time without time zone, boolean, boolean);

CREATE FUNCTION sl_insert_night(new_start_date date, 
    new_start_time time without time zone,
    new_start_no_data boolean,
    new_end_no_data boolean) RETURNS text AS $$
from plpy import spiexceptions
try:
    plan = plpy.prepare("INSERT INTO sl_night (start_date, start_time, start_no_data, end_no_data) \
            VALUES($1, $2, $3, $4)", ["date", "time without time zone", "boolean", "boolean"])
    plpy.execute(plan, [new_start_date, new_start_time, new_start_no_data, new_end_no_data])
except plpy.SPIError, e:
    return "error: SQLSTATE %s" % (e.sqlstate,)
else:
    return "sl_insert_night() succeeded"
$$ LANGUAGE plpythonu;


DROP FUNCTION sl_insert_nap(time without time zone, interval);

CREATE FUNCTION sl_insert_nap(new_start_time time without time zone,
    new_duration interval hour to minute) RETURNS text AS $$
from plpy import spiexceptions
try:
    rv = plpy.execute("SELECT currval('sl_night_night_id_seq') AS my_night_id")
    plan = plpy.prepare("INSERT INTO sl_nap(start_time, duration, night_id) \
            VALUES($1, $2, $3)", ["time without time zone", 
            "interval hour to minute", "integer"])
    plpy.execute(plan, [new_start_time, new_duration, rv[0]["my_night_id"]])
except plpy.SPIError, e:
    return "error: SQLSTATE %s" % (e.sqlstate,)
else:
    return "sl_insert_nap() succeeded"
$$ LANGUAGE plpythonu;
