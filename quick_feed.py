import create_db
import os, argparse
import directorytools as dt
import formatcheck as fc
from schemaprops import SchemaProps
from easysql import EasySQL
from csv import DictReader, DictWriter
from os import path
import validation
import psycopg2
import create_feed
from datetime import datetime
import zipfile
from shutil import make_archive

parser = argparse.ArgumentParser(description='''This application processes structured
VIP CSV data into a VIP XML document while performing validation on the data.''')

parser.add_argument('directory', action='store', metavar='CSV_DIR',
		    help='the directory containing VIP CSV files')
parser.add_argument('--report-dir', dest='report_dir', required=True, action='store',
		    help='the output directory for reports')
parser.add_argument('--feed-dir', dest='feed_dir', required=True, action='store',
		    help='the output directory for the feed')
parser.add_argument('--tmp-dir', dest='tmp_dir', default='/tmp', action='store',
		    help='a temp directory for parsing')
parser.add_argument('--state', dest='state', required=True, action='store',
		    help='the abbreviation of the state')
parser.add_argument('--county', dest='county', default='', action='store',
                    help='the full name of the county')
parser.add_argument('--data-type', dest='data_type', default='db_flat', action='store',
                    choices=['db_flat', 'element_flat', 'feed'],
                    help='the VIP CSV data file type (NB: only current supported type is "db_flat")')
parser.add_argument('--voterfile', dest='vf', action='store_true',
                    help='flag to validate the data with the assumption it\'s from a voterfile')
parser.add_argument('--dbname', dest='database', action='store',
                    help='the database name')
parser.add_argument('--dbuser', dest='username', action='store',
                    help='username to connect to the database')
parser.add_argument('--dbpass', dest='password', action='store',
                    help='password to connect to the database')
parser.add_argument('--schema', dest='schema_url', default='http://votinginfoproject.github.io/vip-specification/vip_spec_v3.0.xsd', action='store',
                    help='the url to a VIP schema version')

args = parser.parse_args()

loc_dict = {
    "state": args.state,
    "county": args.county
}

data_type = args.data_type #db_flat, element_flat, feed

SCHEMA_URL = args.schema_url
LOCATION = "vip_{state}{county}".format(**loc_dict)
DATA_DIR = os.path.abspath(args.directory)
REPORT_DIR = os.path.abspath(args.report_dir)
FEED_DIR = os.path.abspath(args.feed_dir)
TMP_DIR = os.path.abspath(args.tmp_dir)
DUP_HEADER = ['element_name','id','duplicate_id']
ERROR_HEADER = ['base_element','type','problem_element','id','code']
WARNING_HEADER = ['base_element','type','problem_element','id','code']
SS_ERROR_HEADER = ['id','problem_element','code']
SS_WARNING_HEADER = ['id','problem_element','code']
SS_DUP_HEADER = ['id','duplicate_id']
REPORT_FILE = "feed_reports/{0}_report".format(LOCATION)
vf = args.vf

def files_ename_by_extension(directory, extension):
    f_list = {}
    for f in os.listdir(directory):
	element_name, f_exten = f.lower().split(".")
	if f_exten == extension:
	    f_list[f] = element_name
    return f_list

def check_db_flat(data_dir, sp):
    file_list = files_ename_by_extension(data_dir, "txt")
    invalid_files = fc.invalid_files(data_dir, file_list, sp.full_header_data("db"))
    valid_files = []
    for k, v in file_list.iteritems():
	if k not in invalid_files:
	    valid_files.append(k)

    return {"invalid_files":invalid_files, "valid_files":valid_files}

def get_fips(loc_dict):
    with open('fips.csv', 'r') as r:
	reader = DictReader(r)
	if len(loc_dict["county"]) > 0:
	    for row in reader:
		if row['State'].lower() == loc_dict['state'].lower() and row['Cty'].lower() == loc_dict['county'].lower():
		    return row['Fips5']
        else:
            for row in reader:
                if row['State'].lower() == loc_dict['state'].lower():
                    return row['StateFips']
			    
def write_issues(report_dir, issues, issue_header, issue_file):
    if len(issues) == 0:
	return
	with open(path.join(report_dir, issue_file), "w") as w:
	    writer = DictWriter(w, fieldnames=issue_header)
	    writer.writeheader()
	    for issue in issues:
		writer.writerow(issue)

def write_report(report_dir, counts, file_issues, issue_counts, loc_dict, fname):
    with open(path.join(report_dir, fname), "w") as w:
	w.write("Time Processed: {0}\n\n".format(datetime.now().isoformat()))
	w.write("----------------------\nSource Data\n----------------------\n\n")
	w.write("State: {state}\nCounty: {county}\n\n".format(**loc_dict))
	w.write("----------------------\nFile Report\n----------------------\n\n")
	w.write("Invalid Files: {invalid_files}\nValid Files: {valid_files}\n\n".format(**file_issues))
	w.write("----------------------\nElement Counts\n----------------------\n\n")

	for k,v in counts.iteritems():
	    w.write("{0}: {1}\n".format(k,v))

        w.write("\n\n----------------------\nReported Issues Count\n----------------------\n\n")

        for k,v in issue_counts.iteritems():
            w.write("{0}: {1}\n".format(k,v))
		
fips = get_fips(loc_dict)

#db settings
db_type = "postgres"
host = "localhost"
db_name = args.database
username = args.username
password = args.password
conn = psycopg2.connect(host=host, database=db_name, user=username, password=password)

create_db.clear_setup_db(LOCATION, conn)

db = EasySQL(host, db_name, username, password)

process_dir = path.join(TMP_DIR, "vip_feed")
dt.clear_or_create(process_dir)
dt.clear_or_create(REPORT_DIR)

sp = SchemaProps(SCHEMA_URL)

#should have a call to get file type here sometime, and then call the necessary functions
#data_type = get_type(DIR)

#the db_flat type should not be an issue, because by the time it gets here, the data should have already been converted
#if data_type == "db_flat":

file_issues = check_db_flat(DATA_DIR, sp)
counts, errors, warnings = validation.file_validation(
    DATA_DIR, process_dir, file_issues["valid_files"], sp)

for f in os.listdir(process_dir):
    with open(path.join(process_dir, f), "r") as r:
	reader = DictReader(r)
	db.copy_upload(f.split(".")[0], reader.fieldnames, r.name)

duplicates, db_errors = validation.db_validation(conn, sp)
errors += db_errors
ss_errors, ss_warnings, ss_duplicates = validation.ss_validation(conn, sp, vf)
write_issues(REPORT_DIR, errors, ERROR_HEADER, "feed_errors.txt")
write_issues(REPORT_DIR, warnings, WARNING_HEADER, "feed_warnings.txt")
write_issues(REPORT_DIR, duplicates, DUP_HEADER, "feed_duplicates.txt")
write_issues(REPORT_DIR, ss_errors, SS_ERROR_HEADER, "street_segment_errors.txt")
write_issues(REPORT_DIR, ss_warnings, SS_WARNING_HEADER, "street_segment_warnings.txt")
write_issues(REPORT_DIR, ss_duplicates, SS_DUP_HEADER, "street_segment_duplicates.txt")
issue_counts = {'errors':len(errors),
		'warnings':len(warnings),
		'duplicates':len(duplicates),
		'street_segment_errors':len(ss_errors),
		'street_segment_warnings':len(ss_warnings),
		'street_segment_duplicates':len(ss_duplicates)}
write_report(REPORT_DIR, counts, file_issues, issue_counts, loc_dict, "report_summary.txt")

#Validations - Need a vf vs. segment flag, so that the queries can be run accordingly (exact match vs. range check)
feed_file = create_feed.create_feed(conn, sp, FEED_DIR, fips)
make_archive(REPORT_FILE, "zip", REPORT_DIR)
zf = zipfile.ZipFile(feed_file.split(".")[0] + ".zip", mode="w")
print feed_file
zf.write(feed_file, os.path.basename(feed_file), zipfile.ZIP_DEFLATED)
zf.close()
os.remove(feed_file)
