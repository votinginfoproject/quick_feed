#!/usr/bin/env python
# -- coding: utf-8 --
from lxml import etree
import psycopg2
from psycopg2 import extras
from schemaprops import SchemaProps
from feedconf import Schema, Output

def create_xml(row, cursor, e):
	base = etree.Element(e, attrib={'id':str(row['id'])})
	addresses = {}
	for key in Schema.E_DICT[e]:
		if key.find('address') >= 0:
			for a_type in Schema.ADDRESS_TYPES:
				if key.startswith(a_type):
					if a_type not in addresses:
						addresses[a_type] = etree.Element(a_type)
					temp_add = etree.Element(key[len(a_type)+1:])
					temp_add.text = str(row[key])
					addresses[a_type].append(temp_add)
		elif e in Schema.UNBOUNDED and key in Schema.UNBOUNDED[e]: #TODO: Candidate sort_order, check on referendum/ballot_response_id
			cursor.execute("SELECT {0} from {1}_{2} where {1}_id = {3}".format(key, e, key[:-3], row['id']))
			for ub_row in cursor.fetchall():
				temp_elem = etree.Element(key)
				temp_elem.text = str(ub_row[key])
				base.append(temp_elem)
		elif not row[key] or len(str(row[key]).strip()) == 0:
			continue
		else:
			temp_elem = etree.Element(key)
			temp_elem.text = str(row[key])
			base.append(temp_elem)
	if len(addresses) > 0:
		for key, val in addresses.iteritems():
			base.append(val)		
	return base

def create_feed(conn, sp, feed_dir, fips):

	cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
	feed_file = feed_dir + Output.XML_FILE.format(fips)
	with open(feed_file, "w") as w:
		w.write(Output.HEADER + "\n")
		for e in Schema.E_ORDER:
			cursor.execute("SELECT * FROM " + e)
			for row in cursor.fetchall():
				w.write(etree.tostring(create_xml(row, cursor, e), pretty_print=True))
		w.write(Output.FOOTER)
	return feed_file
