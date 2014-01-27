#!/usr/bin/env python
# -- coding: utf-8 --
from lxml import etree
from os import path
import psycopg2
from psycopg2 import extras
from schemaprops import SchemaProps
from feedconf import Schema, Output

def create_xml(row, cursor, e):
	base = etree.Element(e, attrib={'id':str(row['id'])})
	addresses = {}
	for key in Schema.E_DICT[e]:
		if e in Schema.UNBOUNDED and key in Schema.UNBOUNDED[e]: #TODO: Candidate sort_order, check on referendum/ballot_response_id
			cursor.execute("SELECT {0} from {1}_{2} where {1}_id = {3}".format(key, e, key[:-3], row['id']))
			for ub_row in cursor.fetchall():
				temp_elem = etree.Element(key)
				temp_elem.text = str(ub_row[key])
				base.append(temp_elem)
		elif not row[key] or len(str(row[key]).strip()) == 0:
			continue
		elif key.find('address') >= 0:
			for a_type in Schema.ADDRESS_TYPES:
				if key.startswith(a_type):
					if a_type not in addresses:
						addresses[a_type] = etree.Element(a_type)
					temp_add = etree.Element(key[len(a_type)+1:])
					temp_add.text = str(row[key])
					addresses[a_type].append(temp_add)
		else:
			temp_elem = etree.Element(key)
			temp_elem.text = str(row[key])
			base.append(temp_elem)
	if len(addresses) > 0:
		for key, val in addresses.iteritems():
			base.append(val)		
	return base

def create_source(row):
	base = etree.Element('source', attrib={'id':str(row['id'])})
	for key in Schema.E_DICT['source']:
		if not row[key] or len(str(row[key]).strip()) == 0:
			continue
		else:
			temp_elem = etree.Element(key)
			if key == "datetime":
				temp_elem.text = 'T'.join(str(row[key]).split(" "))
			else:
				temp_elem.text = str(row[key])
			base.append(temp_elem)
	return base

def create_feed(conn, sp, feed_dir, fips):
	cursor = conn.cursor(cursor_factory=extras.RealDictCursor)

        ## Mega hack for now until I have time to come up with a
        ## permanent fix
        cursor.execute("SELECT date FROM election")
        row = cursor.fetchone()
        election_date = row['date']
        feed_file = path.join(feed_dir, Output.XML_FILE.format(fips, election_date))

	with open(feed_file, "w") as w:
		w.write(Output.HEADER + "\n")
		cursor.execute("SELECT * FROM source")
		w.write(etree.tostring(create_source(cursor.fetchall()[0]), pretty_print=True))
		for e in Schema.E_ORDER:
			cursor.execute("SELECT * FROM " + e)
			for row in cursor.fetchall():
				w.write(etree.tostring(create_xml(row, cursor, e), pretty_print=True))
		w.write(Output.FOOTER)
	return feed_file
