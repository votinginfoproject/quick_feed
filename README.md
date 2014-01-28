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