# Command-line program which exports JSON files to text, HTML, epub, or mobi.
import sys
import log_conversion
from clint import args

usage = """
Reads all files from output_path and generates the specified content type in the
output directory.

Flags (may occur in any order):

-f format [optional] Format to generate: may be "text", "html", "epub", or
"mobi". Defaults to "text".

-i path Directory from which to read input files

-o path Directory to which to write output files; or the path to the output
file, if an ebook is to be created

Usage:
Generate text: python -i json_dir -o text_dir
Generate html: python -f html -i json_dir -o html_dir
Generate epub: python -f epub -i json_dir -o epub_dir/my_book.epub
Generate mobi: python -f mobi -i json_dir -o mobi_dir/my_book.mobi

Note that the mobi version will create an epub file as an intermediate step and
delete it after conversion is complete.
"""

def show_usage():
    "Print the usage message and exit the script."
    print usage
    sys.exit()

if args.get(0) is "--help":
    show_usage()
else:
    groups = dict(args.grouped)

    if not (groups.has_key("-i") and groups.has_key("-o")):
        show_usage()
    else:
        format = groups["-f"][0] if groups.has_key("-f") else "text"
        input_path = groups["-i"][0]
        output_path = groups["-o"][0]

    if format == "text":
        exporter = log_conversion.LogExporter()
        exporter.output_directory(input_path, output_path)

    elif format == "html":
        exporter = log_conversion.HTMLExporter()
        exporter.output_directory(input_path, output_path)

    elif format == "epub":
        exporter = log_conversion.EpubExporter()
        exporter.output_book(input_path, output_path)

    elif format == "mobi":
        exporter = log_conversion.MobiExporter()
        exporter.output_book(input_path, output_path)
