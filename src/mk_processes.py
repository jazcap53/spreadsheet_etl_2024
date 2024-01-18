# file: src/mk_processes.py
# andrew jarcho
# 2017-02-24


"""
Create and connect the subprocesses that run the extract, transform,
and load stages.

logging_process runs the network logging receiver that allows all 3 stages
to log to the same file.
"""

import subprocess
import time
import argparse

note = 'Runs in debug mode unless -s switch is given.'
parser = argparse.ArgumentParser(description=note)
parser.add_argument('infile_name', help='The name of a .csv file to read')
parser.add_argument('-s', '--store', help='Store output in database',
                    action='store_true')
args = parser.parse_args()

# remove the --store argument from the args Namespace, if present
args_dict = args.__dict__
# args_dict[store] has been set to True if present
store_in_db = str(args_dict.pop('store', False))

logging_process = subprocess.Popen(
    ['./src/logging/receiver.py'],
)

time.sleep(1)

extract_process = subprocess.Popen(
    ['./src/extract/run_it.py', args.infile_name],
    stdout=subprocess.PIPE,
)

time.sleep(5)

transform_process = subprocess.Popen(
    ['./src/transform/do_transform.py'],
    stdin=extract_process.stdout,
    stdout=subprocess.PIPE,
)

time.sleep(6)

load_process = subprocess.Popen(
    ['./src/load/load.py', store_in_db],
    stdin=transform_process.stdout,
)

time.sleep(15)

extract_process.terminate()
transform_process.terminate()
load_process.terminate()
logging_process.terminate()
