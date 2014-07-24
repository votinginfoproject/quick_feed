import csv
from os import path
from ConfigParser import ConfigParser

def invalid_config_sections(directory, config_file, section_props):

	config = ConfigParser()
	config.read(config_file)
	sections = config.sections()
	invalid_sections = []
	for s in sections:
		if s not in section_props:
			invalid_sections.append(s)
		elif not config.has_option(s, "file_name") or not config.has_option(s, "header"):
			invalid_sections.append(s)
		elif not path.exists(directory + config.get(s, "file_name")):
			invalid_sections.append(s)
		else:
			header = config.get(s, "header").split(",")
			if any(h not in section_props[s] for h in header):
				invalid_sections.append(s)
				continue
			with open(directory + config.get(s, "file_name")) as f:
				fdata = csv.reader(f)
				try:
					if len(fdata.next()) != len(header):
						invalid_sections.append(s)
				except:
					invalid_sections.append(s)
	return invalid_sections

def invalid_files(directory, file_list, file_props):
	invalid_files = []
	print "Checking for invalid filenames and invalid fieldnames"
 	for k, v in file_list.iteritems():
 		if k.lower()[:-4] not in file_props:
 			print "  FAILED: " + k + " - filename does not match expected filenames"
 			invalid_files.append(k)
 		else:
			with open(path.join(directory, k)) as f:
				try:
					fdata = csv.DictReader(f)
				except:
					print "  FAILED: " + k + " - CSV reading failed"
					invalid_files.append(f)
					continue
				invalid_fields = []
				for h in fdata.fieldnames:
					if h.lower() not in file_props[v]:
						invalid_fields.append(h.lower())
				if invalid_fields:
					print "  FAILED: " + k + " - invalid fields [" + ",".join(invalid_fields) + "]"
					invalid_files.append(k)
				else:
					print "PASSED: " + k
	return invalid_files
