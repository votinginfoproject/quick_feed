# Quick Feed #
Quick Feed is a series of interconnected scripts that parses CSV files in the [Voting Information Project (VIP) CSV format](https://github.com/votinginfoproject/csv-templates) and&mdash;assuming no serious issues&mdash;builds the data into a [VIP XML](http://votinginfoproject.github.com/vip-specification) document. It also provides an audit of the build process, ranging from a high-level summary to low-level reports on data quality.

While these scripts are currently the method of VIP XML document creation, it will remain largely under-developed and undeveloped due to being eventually superseded by the new data processing pipeline, [Metis](https://github.com/votinginfoproject/Metis). Many of the inclusions are admittedly hacks to make the building process a bit simpler.

## Requirements ##
Quick Feed requires the following components to be installed, first:

* Python 2.7
* PostgreSQL 9+

To follow the installation instructions below, [homebrew](http://brew.sh/) is also needed.

## Installation ##
_The following instructions assume installation on a Mac._

First, if you haven't already, install [homebrew](http://brew.sh/). Life will become infinitely easier.

Install both python and postgres using homebrew

    $ brew install postgres python

Clone the repository

    $ git clone https://github.com/votinginfoproject/quick_feed.git

Install virtualenv, set up a virtual environment, and install the required libraries

    $ pip install virtualenv
    $ virtualenv --no-site-packages ~/path/to/virtualenv
    $ source ~/path/to/virtualenv/bin/activate
    $ pip install -r requirements.txt

At this point, as long as the other dependencies are set up correctly, quick_feed will now work with the proper arguments

    usage: quick_feed.py [-h] --report-dir REPORT_DIR --feed-dir FEED_DIR
			 [--tmp-dir TMP_DIR] --state STATE [--county COUNTY]
			 [--data-type {db_flat,element_flat,feed}] [--voterfile]
			 [--dbname DATABASE] [--dbuser USERNAME]
			 [--dbpass PASSWORD] [--schema SCHEMA_URL]
			 CSV_DIR

    This application processes structured VIP CSV data into a VIP XML document
    while performing validation on the data.

    positional arguments:
      CSV_DIR               the directory containing VIP CSV files

    optional arguments:
      -h, --help            show this help message and exit
      --report-dir REPORT_DIR
                            the output directory for reports
      --feed-dir FEED_DIR   the output directory for the feed
      --tmp-dir TMP_DIR     a temp directory for parsing
      --state STATE         the abbreviation of the state
      --county COUNTY       the full name of the county
      --data-type {db_flat,element_flat,feed}
                            the VIP CSV data file type (NB: only current supported
                            type is "db_flat")
      --voterfile           flag to validate the data with the assumption it's
                            from a voterfile
      --dbname DATABASE     the database name
      --dbuser USERNAME     username to connect to the database
      --dbpass PASSWORD     password to connect to the database
      --schema SCHEMA_URL   the url to a VIP schema version

## Running ##
A successful run takes a while and then exits gracefully and produces have a report_summary.txt file where ever you pointed the reports directory at. If things went well, it also produces the feed wherever you pointed the feed output at. Check the reports_summary.txt for errors, and see other accompanying error files to see if anything needs to be cleaned up.

However, more than likely there will be data file errors that prevent a report from being generated. See the section below for some of the typical errors. In these cases you'll most likely get a stack trace output, and have to use that as your guide to figuring out the type of error you encountered.

# Kinds of Data file errors
1. Non-ascii characters. The data somewhat frequently has non-ascii characters that kill the feed generation process. It'll give you the 0xNN character code, so then you can google the code, find the character, copy it, and then do a search for it and replace it with whatever is appropriate. Common non-ascii characters found include: curly single and double quotes and em dashes. Referenda might also include things like the Section Mark character.
2. Files need to be named after the tables they are put into, and also need column names appropriately named as well. So far all I can suggest is find a good data set and use it as a guide, unless you want to pick apart the schema from one of the python files (feedconf.py)
3. Invalid field inputs. Some of the schema fields are enums, and while they handily accept an empty string value, if the export has the value NULL, this will fail. I'm sure there are many other examples of this.
4. No election. Every import needs an election to base the data off of, so if election.txt/election.csv is missing, this will fail with an obscure error that points to a line in the file trying to read the date from a database cursor/result set.
5. More than one election. Also, there should only be a single election in the feed building stage. Fun!
6. Non-data files in data directory. The import is very fragile, and expects all the files in the directory to be part of the import and fails if some are not.


