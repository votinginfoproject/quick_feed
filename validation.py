import csv
from schemaprops import SchemaProps
from shutil import copy
import re
from time import strptime
import psycopg2
from psycopg2 import extras

LOCALITY_TYPES = ['county','city','town','township','borough','parish','village','region']
ZIPCODE_REGEX = re.compile("\d{5}(?:[-\s]\d{4})?")
EMAIL_REGEX = re.compile("[a-zA-Z0-9+_\-\.]+@[0-9a-zA-Z][.-0-9a-zA-Z]*.[a-zA-Z]")
URL_REGEX = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))")
PHONE_REGEX = re.compile("1?\s*\W?\s*([2-9][0-8][0-9])\s*\W?\s*([2-9][0-9]{2})\s*\W?\s*([0-9]{4})(\se?x?t?(\d*))?")
VALID_DIRECTIONS = ['n','s','e','w','nw','ne','sw','se','north','south','east','west','northeast','northwest','southeast','southwest']

def file_validation(data_dir, process_dir, valid_files, sp):
	
	feed_ids = set([])
	error_data = []
	warning_data = []
	element_counts = {}

	for f in valid_files:
		element_name, extension = f.lower().split(".")
		with open(data_dir + f, "r") as reader, open(process_dir + f, "w") as writer:
			r = csv.DictReader(reader)
			w = csv.DictWriter(writer, fieldnames=[fn.lower() for fn in r.fieldnames])
			w.writeheader()
			
			dict_fields = sp.header("db", element_name)
			type_vals = sp.type_data("db", element_name)
			
			row_count = 0
			
			for row in r:
				type_error = False
				row_count += 1
				row = dict((k.lower(), v.strip()) for k,v in row.iteritems())
				for k in row:
					report = validate(k, type_vals[k]["type"], row, type_vals[k]["is_required"])
					if report is not None:
						report["base_element"] = element_name
						report["problem_element"] = k 
						if "id" in row:
							report["id"] = row["id"]
						else:
							report["id"] = "xxx"
						if report["type"] == "error":
							error_data.append(report)
							if report["code"] == "type_error":
								type_error = True
						else:
							warning_data.append(report)
				if "id" in row:
					if element_name == "source":
						row["id"] = 1
					#elif element_name == "election":
					#	row["id"] = 4000 
					if row["id"] not in feed_ids:
						feed_ids.add(row["id"])
					else:
						error_data.append({'base_element':element_name,'type':'error','problem_element':'id','id':row["id"],'code':'duplicate_ids'})
						continue
				if not type_error:
					w.writerow(row)
			element_counts[element_name] = str(row_count)
	return element_counts, error_data, warning_data

def validate(key, xml_type, row, required):

	if len(row[key]) <= 0 or row[key].lower() in ["none","n/a","-","na"]: 
		if required == "true":
			return {"type":"error", "code":"missing_required"}
	elif xml_type == "xs:integer":
		try:
			int(row[key])
			if (key == "end_house_number" or key == "start_house_number") and int(row[key]) == 0:
				return {"type":"error", "code":"type_error"}
			elif (key == "start_apartment_number" or key == "end_apartment_number") and int(row[key]) == 0:
				return {"type":"error", "code":"apartment_number_error"}
		except:
			return {"type":"error", "code":"type_error"}
	elif xml_type == "xs:string":
		if row[key].find("<") >= 0: #need to add in other invalid character checks
			return {"type":"error", "code":"invalid_string"}
		elif key == "zip" and not ZIPCODE_REGEX.match(row[key]):
			return {"type":"warning", "code":"invalid_zip"}
		elif key == "email" and not EMAIL_REGEX.match(row[key]):
			return {"type":"warning", "code":"invalid_email"}
		#elif key.endswith("_url") and not URL_REGEX.match(row[key]):
		#	return {"type":"warning", "code":"invalid_url"}
		elif key == "state" and len(row[key]) != 2:
			return {"type":"warning", "code":"invalid_state_abbrev"}
		elif key == "locality" and row[key].lower() not in LOCALITY_TYPES:
			return {"type":"error", "code":"invalid_locality"}
		elif (key == "phone" or key == "fax") and not PHONE_REGEX.match(row[key].lower()):
			return {"type":"warning", "code":"invalid_phone"}
		elif key.endswith("_direction") and row[key].lower().replace(' ','') not in VALID_DIRECTIONS:
			return {"type":"error", "code":"invalid_street_dir"}
		elif key.find("hours") >= 0 and (row[key].find("to") < 0 and row[key].find("-") < 0):#can be improved, just a naive check to make sure there is some hour range value
			return {"type":"warning", "code":"invalid_hour_range"}
	elif xml_type == "xs:date":
		try:
			strptime(row[key],"%Y-%m-%d")
		except:
			return {"type":"error", "code":"invalid_iso_date"}
	elif xml_type == "xs:dateTime":
		try:
			strptime(row[key],"%Y-%m-%dT%H:%M:%S")
		except:
			return {"type":"error", "code":"invalid_iso_datetime"}
	elif xml_type == 'yesNoEnum':
		if row[key].lower() not in ['yes','no']:
			return {"type":"error", "code":"invalid_yesnoenum"}
	elif xml_type == 'oebEnum':
		if row[key].lower() not in ['odd','even','both']:
			return {"type":"error", "code":"invalid_oebenum"}
	return None

def db_validation(conn, sp):
	
	cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
	table_columns = sp.full_header_data("db")
	base_tables = sp.key_list("element")
	tables = table_columns.keys()
	duplicates = []
	errors = []
	
	for t in tables:
		if t == "street_segment" or t.endswith("result"):
			continue
		join_comparisons = {}
		query = "SELECT t1.id as id, t2.id as duplicate_id FROM {0} t1, {0} t2 WHERE ".format(t) 
		query += ' AND '.join(['t1.{0}=t2.{0}'.format(c) for c in table_columns[t] if c != "id"])
		query += ' AND t1.id != t2.id'
		cursor.execute(query)
		for row in cursor.fetchall():
			duplicates.append({"element_name":t,"id":row['id'],"duplicate_id":row['duplicate_id']})

		for c in table_columns[t]:
			if c.endswith("_id") and c[:-3] in tables:
				cursor.execute("SELECT {0} FROM {1} WHERE {0} IS NOT NULL AND {0} NOT IN (SELECT id FROM {2})".format(c, t, c[:-3]))
				for row in cursor.fetchall():
					errors.append({'base_element':t,'problem_element':c,'type':'error','id':row[c], 'code':'orphaned_object'})
	return duplicates, errors

def ss_validation(conn, sp, vf):
	
	cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
	errors = []
	warnings = []
	duplicates = []
	
	if not vf:
		cursor.execute("SELECT id from street_segment WHERE start_house_number > end_house_number")
		for row in cursor.fetchall():
			errors.append({'id':row['id'],'problem_element':'start-end_house_number','code':'invalid_house_range'})
		cursor.execute("SELECT id FROM street_segment WHERE odd_even_both = 'odd' AND (mod(start_house_number,2) = 0 OR mod(end_house_number,2) = 0)")
		for row in cursor.fetchall():
			warnings.append({'id':row['id'],'problem_element':'odd_even_both','code':'unmatching_oebnumber'})
		cursor.execute("SELECT id FROM street_segment WHERE odd_even_both = 'even' AND (mod(start_house_number,1) = 0 OR mod(end_house_number,1) = 0)")
		for row in cursor.fetchall():
			warnings.append({'id':row['id'],'problem_element':'odd_even_both','code':'unmatching_oebnumber'})
		cursor.execute("SELECT s1.id AS id1, s1.start_house_number AS start1, s1.end_house_number AS end1, s1.precinct_id AS precinct1, s2.id AS id2, s2.start_house_number AS start2, s2.end_house_number AS end2, s2.precinct_id AS precinct2 FROM street_segment s1, street_segment s2 WHERE s1.id != s2.id AND s1.start_house_number BETWEEN s2.start_house_number AND s2.end_house_number AND s1.odd_even_both = s2.odd_even_both AND s1.non_house_address_street_direction IS NOT DISTINCT FROM s2.non_house_address_street_direction AND s1.non_house_address_street_suffix IS NOT DISTINCT FROM s2.non_house_address_street_suffix AND s1.non_house_address_street_name = s2.non_house_address_street_name AND s1.non_house_address_city = s2.non_house_address_city AND s1.non_house_address_zip = s2.non_house_address_zip")
		for row in cursor.fetchall():
			if row['precinct1'] != row['precinct2']:
				errors.append({'id':row['id1'],'problem_element':row['id2'],'code':'segment_overlap_precinct_mismatch'})
			elif row['start1'] == row['start2'] and row['end1'] == row['end2']:
				duplicates.append({'id':row['id1'],'duplicate_id':row['id2']})
			else:
				warnings.append({'id':row['id1'],'problem_element':row['id2'],'code':'segment_overlap_precinct_match'})
	else:
		cursor.execute("SELECT id FROM street_segment WHERE odd_even_both = 'odd' AND mod(start_house_number,2)")
		for row in cursor.fetchall():
			warnings.append({'id':row['id'],'problem_element':'odd_even_both','code':'unmatching_oebnumber'})
		cursor.execute("SELECT id FROM street_segment WHERE odd_even_both = 'even' AND mod(start_house_number,1)")
		for row in cursor.fetchall():
			warnings.append({'id':row['id'],'problem_element':'odd_even_both','code':'unmatching_oebnumber'})
		cursor.execute("SELECT s1.id AS id1, s1.start_house_number AS start1, s1.precinct_id AS precinct1, s2.id AS id2, s2.start_house_number AS start2, s2.precinct_id AS precinct2 FROM street_segment s1, street_segment s2 WHERE s1.id != s2.id AND s1.start_house_number = s2.start_house_number AND s1.non_house_address_street_direction IS NOT DISTINCT FROM s2.non_house_address_street_direction AND s1.non_house_address_street_suffix IS NOT DISTINCT FROM s2.non_house_address_street_suffix AND s1.non_house_address_street_name = s2.non_house_address_street_name AND s1.non_house_address_city = s2.non_house_address_city AND s1.non_house_address_zip = s2.non_house_address_zip")
		for row in cursor.fetchall():
			if row['precinct1'] != row['precinct2']:
				errors.append({'id':row['id1'],'problem_element':row['id2'],'code':'segment_overlap_precinct_mismatch'})
			elif row['start1'] == row['start2']:
				duplicates.append({'id':row['id1'],'duplicate_id':row['id2']})
			else:
				warnings.append({'id':row['id1'],'problem_element':row['id2'],'code':'segment_overlap_precinct_match'})
	return errors, warnings, duplicates
