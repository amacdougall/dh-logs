# Command-line program which imports log files to create JSON output;
# this output can then be fed to export.py.
from log_conversion import LogImporter
from clint import args

usage = """
Reads all files from input_dir and generates JSON files in output_dir with
equivalent names.

Usage: python import.py input_dir output_dir
"""

if args.get(0) is "--help" or len(args) != 2:
    print usage
else:
    input_dir, output_dir = list(args[0:])

    importer = LogImporter()
    importer.process_directory(input_dir, output_dir)
