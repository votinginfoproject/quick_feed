from urllib import urlopen
from schema import Schema
import psycopg2

#for string formatting, "xs:" changes to "xml_" because ":" within format
#interprets the format statement as a range
TYPE_CONVERSIONS = {"id":"BIGSERIAL PRIMARY KEY", "xml_string":"TEXT",
			"xml_integer":"BIGINT", "xml_dateTime":"TIMESTAMP", 
			"timestamp": "TIMESTAMP", "xml_date":"DATE",
			"int": "INTEGER", "boolean": "BOOLEAN",
			"date_created": "DEFAULT CURRENT_TIMESTAMP",
			"date_modified": "DEFAULT CURRENT_TIMESTAMP"}
SCHEMA_URL = "http://votinginfoproject.github.io/vip-specification/vip_spec_v3.0.xsd"

def create_enum(simple, simple_elements, cursor, connection):

	cursor.execute("DROP TYPE IF EXISTS {0} CASCADE".format(simple))
	cursor.execute("CREATE TYPE {0} AS ENUM %s".format(simple), (tuple(simple_elements),))
	connection.commit()

def create_relational_table(name, element, cursor, connection):

	ename1 = name
	ename2 = element["name"][:element["name"].find("_id")]

	cursor.execute("DROP TABLE IF EXISTS {0}_{1}".format(ename1, ename2))
	create_statement = "CREATE TABLE {0}_{1} (id {{id}}, {0}_id {{xml_integer}}, {1}_id {{xml_integer}}".format(ename1, ename2)

	if "simpleContent" in element and "attributes" in element["simpleContent"]:
		for attr in element["simpleContent"]["attributes"]:
			create_statement += ", {0} {1}".format(attr["name"]," {"+attr["type"]+"}")

	create_statement += ", UNIQUE({0}_id, {1}_id))".format(ename1, ename2)
	create_statement = create_statement.replace("xs:", "xml_")
	create_statement = create_statement.format(**TYPE_CONVERSIONS)
	cursor.execute(create_statement)
	connection.commit()
	
def create_table(name, elements, cursor, connection, complex_types, simple_types, schema): 
	cursor.execute("DROP TABLE IF EXISTS {0}".format(name))
	create_statement = "CREATE TABLE {0} (id {{id}}".format(name)
	
	if name not in complex_types:
		create_statement += ", feed_id {xml_integer}"

	for e in elements:
		if not "name" in e:
			if "elements" in e:
				create_relational_table(name, e["elements"][0], cursor, connection)
		elif e["type"] == "complexType":
			if "simpleContent" in e:
				create_relational_table(name, e, cursor, connection)
		elif e["type"].startswith("xs:"):
			if "maxOccurs" in e and e["maxOccurs"] == "unbounded":
				create_relational_table(name, e, cursor, connection)
			else:
				create_statement += ", {0} {1}".format(e["name"], " {"+e["type"]+"}")
		else:
			if e["type"] in simple_types:
				create_statement += ", {0} {1}".format(e["name"], e["type"])
			elif e["type"] in complex_types:
				sub_schema_elements = schema.get_sub_schema(e["type"])["elements"]
				for s_s_e in sub_schema_elements:
					create_statement += ", {0}_{1} {2}".format(e["name"], s_s_e["name"], " {"+s_s_e["type"]+"}")

	if name not in complex_types:
		create_statement += ", UNIQUE(feed_id)"
	create_statement += ")"
	create_statement = create_statement.replace("xs:", "xml_")
	create_statement = create_statement.format(**TYPE_CONVERSIONS)

	cursor.execute(create_statement)		
	connection.commit()

def clear_setup_db(location, conn, schema=Schema(SCHEMA_URL)):

	cursor = conn.cursor()

	complex_types = schema.get_complexTypes()
	simple_types = schema.get_simpleTypes()
	elements = schema.get_element_list("element", "vip_object")

	for simple in simple_types:
		create_enum(simple, schema.get_element_list("simpleType", simple), cursor, conn)

	for element in elements:
		create_table(element, schema.get_sub_schema(element)["elements"], cursor, conn, complex_types, simple_types, schema)

