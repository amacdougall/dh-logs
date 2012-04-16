# process OpenRPG HTML-like logs to JSON
import os
import re
import json
from BeautifulSoup import BeautifulSoup
import template


def sort(input_list):
    """Returns a sorted shallow copy of the input list. There's gotta be a
    native command for this, I'm just offline."""
    output_list = list(input_list)
    output_list.sort()
    return output_list


# "importing" in this case means converting the data from its mishmash
# of formats and storing it all in consistent JSON files; from there,
# it can be exported to plaintext, HTML, ebook, etc.
class LogImporter(object):
    """Converts OpenRPG log lines, files, or whole directories to JSON data."""

    def __init__(self):
        self.extension_pattern = r"\.(html|txt)$"
        # openRPG timestamp pattern
        self.timestamp_pattern = r"^\[.+\d{4}\] : "
        # if present in the first 10 lines, this is a Campfire log
        self.campfire_log_pattern = r"^\s+<title>Campfire"

        # openRPG content patterns, through the years
        self.content_patterns = (
            (r"^<[Bb]>\(\d+\) (.+)</[Bb]>: <font", self.statement_v1),
            (r"^<[Bb]>(.+)</[Bb]>: <font", self.statement_v2),
            (r"^<p><b>(.+)</b>: ", self.statement_v3),
            (r"^<font color='#\d{6}'>\*{2} \(\d+\) ", self.emote_v1),
            (r"^<font color='#\d{6}'>\*{2}", self.emote_v2),
            (r"^<p>\*{2} ", self.emote_v3),
        )

        self.log_file = None
        self.log_filename = None

    def log(self, message):
        if self.log_filename is not None:
            if self.log_file is None:
                self.log_file = file(self.log_filename, "w")
            self.log_file.write(message + "\n")
            self.log_file.flush()

    def strip_timestamp(self, line):
        return re.sub(self.timestamp_pattern, "", line)

    def statement_v1(self, line):
        """Parses a statement in the following format:
            <B>(123) Alan</B>: <font color='#800040'>Example.</font><br>
        """
        self.log("Parsing as v1 statement: %s" % line)
        parsed = BeautifulSoup(line)
        # build log entry
        return {
            "type": "statement",
            "player": re.sub(r"^\(\d+\) ", "", parsed.b.renderContents()),
            "content": parsed.font.renderContents(),
        }

    def statement_v2(self, line):
        """Parses a statement in the following format:
            <B>Alan</B>: <font color='#800040'>Example sentence.</font><br>
        """

        self.log("Parsing as v2 statement: %s" % line)
        parsed = BeautifulSoup(line)
        # return log entry
        return {
            "type": "statement",
            "player": parsed.b.renderContents(),
            "content": parsed.font.renderContents(),
        }

    def statement_v3(self, line):
        """Parses a statement in the following format:
            <p><b>Alan</b>: Example sentence.</p>
        """

        self.log("Parsing as v3 statement: %s" % line)
        parsed = BeautifulSoup(line)
        player = parsed.b.extract().renderContents()  # also removes <b> tag
        content = re.sub(r"^: ", "", parsed.p.renderContents())

        # return log entry
        return {
            "type": "statement",
            "player": player,
            "content": content,
        }

    def campfire_statement(self, tag):
        """Parse a statement in Campfire log HTML format. Accepts a
        BeautifulSoup Tag object."""
        player = tag.find("span", {"class": "author"}).renderContents()
        content = tag.find("div", {"class": "body"}).renderContents()

        # return log entry
        return {
            "type": "statement",
            "player": player,
            "content": content,
        }

    def emote_v1(self, line):
        self.log("Parsing as v1 emote: %s" % line)
        parsed = BeautifulSoup(line)
        emote = parsed.font.renderContents()  # gives raw innerHTML
        content = re.search("^\*{2} \(\d+\) (.+) \*{2}", emote).group(1)
        entry = {
            "type": "emote",
            "content": content,
        }
        return entry

    def emote_v2(self, line):
        parsed = BeautifulSoup(line)
        emote = parsed.font.renderContents()  # gives raw innerHTML
        content = re.search("^\*{2} (.+) \*{2}", emote).group(1)
        entry = {
            "type": "emote",
            "content": content,
        }
        return entry

    def emote_v3(self, line):
        parsed = BeautifulSoup(line)
        emote = parsed.p.renderContents()
        content = re.search("^\*{2} (.+) \*{2}", emote).group(1)
        entry = {
            "type": "emote",
            "content": content
        }
        return entry

    def process_openRPG_line(self, line):
        line = self.strip_timestamp(line.strip())
        for pattern, function in self.content_patterns:
            if re.search(pattern, line):
                return function(line)
        return None  # if nothing matched

    def is_campfire_log(self, filename):
        """True if campfire_log_pattern is found in the first 10 lines."""
        log_file = file(filename)
        for n in range(0, 9):
            if re.search(self.campfire_log_pattern, log_file.readline()):
                return True
        return False

    def is_text_log(self, filename):
        """True if filename ends with .txt."""
        return filename.endswith(".txt")

    def process_file(self, input_file, output_file):
        self.log("Processing file: %s -> %s" % (input_file, output_file))

        if self.is_campfire_log(input_file):
            self.log("Converting from Campfire transcript to JSON...")
            log_entries = self.process_campfire_log(input_file)
        elif self.is_text_log(input_file):
            self.log("Converting from text format to JSON...")
            log_entries = self.process_text_log(input_file)
        else:
            self.log("Converting from OpenRPG log to JSON...")
            log_entries = self.process_openRPG_log(input_file)

        json.dump(log_entries, file(output_file, "w"))

    def process_campfire_log(self, input_file):
        """Parse Campfire HTML transcript and return log entries."""
        parsed = BeautifulSoup(file(input_file).read())
        statements = parsed.findAll("tr", {
            "class": re.compile(r"^text_message.+")
        })
        return [self.campfire_statement(statement)
                for statement in statements]

    # this case is so simple we don't need line processing functions
    def process_text_log(self, input_file):
        """Break text file into paragraphs and return one entry per para."""
        lines = [line.strip() for line in file(input_file).readlines()]
        lines = filter(None, lines)  # filter out empty lines
        return [{"type": "text", "content": line} for line in lines]

    def process_openRPG_log(self, input_file):
        input_lines = file(input_file).readlines()
        output_lines = [self.process_openRPG_line(line) for line in input_lines]
        return filter(None, output_lines)  # remove None elements

    def process_directory(self, input_dir, output_dir):
        self.log("Processing dir: %s -> %s" % (input_dir, output_dir))

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        elif not os.path.isdir(output_dir):
            raise "Output directory %s is not a valid directory" % output_dir

        input_filenames = [filename for filename in os.listdir(input_dir)
                           if re.search(self.extension_pattern, filename)]

        for filename in input_filenames:
            # open a new log file for each input file
            self.start_logging()

            input_filename = os.path.join(input_dir, filename)
            output_filename = os.path.join(output_dir, filename)
            output_filename = re.sub(self.extension_pattern, ".json", filename)
            self.process_file(input_filename, output_filename)

            self.stop_logging()

    # utility
    def start_logging(self):
        "Enable log statements."
        if self.log_file is None or self.log_file.closed:
            if self.log_filename is not None:
                self.log_file = file(self.log_filename, "w")

    def stop_logging(self):
        "Disable log statements."
        if self.log_file is not None:
            self.log_file.close()


# all methods in this class assume that the JSON data is sound; empty lines
# so on should have been handled during the archiving stage.
class LogExporter(object):
    """Base class for log entry output. This default implementation generates
    simple UTF-8 text files."""

    def __init__(self):
        self.entry_types = (
            ("text", self.output_text),
            ("statement", self.output_statement),
            ("emote", self.output_emote)
        )
        self.input_extension_pattern = r".json$"
        self.output_file_extension = ".txt"
        self.line_separator = "\n"  # Unix style

    def output_entry(self, log_entry):
        for type, function in self.entry_types:
            if log_entry["type"] == type:
                return function(log_entry)
        # if no entry type existed for this entry:
        raise "No handler for entry type %s" % log_entry["type"]

    def output_text(self, log_entry):
        return self.strip_tags(log_entry["content"])

    def output_statement(self, log_entry):
        return "%s: %s" % (log_entry["player"],
                           self.strip_tags(log_entry["content"]))

    def output_emote(self, log_entry):
        return self.strip_tags(log_entry["content"])

    def output_file(self, input_filename, output_filename):
        """Read the JSON input file and write it as plaintext."""
        lines = [self.output_entry(entry) for entry
                 in json.load(file(input_filename))]
        output_file = file(output_filename, "w")
        output_file.write(self.line_separator.join(lines))
        output_file.write(self.line_separator)  # trailing newline is good form
        output_file.close()

    def output_directory(self, input_dir, output_dir):
        # destructuring bind, in your face
        input_filenames, output_filenames = self.build_file_lists(input_dir, output_dir)

        for input_filename, output_filename in zip(input_filenames, output_filenames):
            self.output_file(input_filename, output_filename)

    # utility
    def build_file_lists(self, input_dir, output_dir):
        self.prepare_directory(output_dir)
        input_filenames = self.build_input_filenames(input_dir)
        output_filenames = self.build_output_filenames(input_dir, output_dir)
        return (input_filenames, output_filenames)

    def prepare_directory(self, output_dir):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        elif not os.path.isdir(output_dir):
            raise "Output directory %s is not a valid directory" % output_dir

    def build_input_filenames(self, input_dir):
        return [os.path.join(input_dir, filename)
                for filename in sort(os.listdir(input_dir))
                if re.search(self.input_extension_pattern, filename)]

    def build_output_filenames(self, input_dir, output_dir):
        # looks a bit weird, but I think it's readable!
        return [os.path.join(output_dir,
                             re.sub(self.input_extension_pattern,
                                    self.output_file_extension,
                                    filename))
                for filename in sort(os.listdir(input_dir))]

    def strip_tags(self, line):
        parsed = BeautifulSoup(line)

        def tag_text(parsed):
            result = []
            for element in parsed.contents:
                if hasattr(element, "contents"):
                    result.append(tag_text(element))
                else:
                    result.append(element)
            return "".join(result)

        return tag_text(parsed)


class HTMLExporter(LogExporter):
    """Generates HTML output; output_directory also creates an index file."""
    def __init__(self):
        LogExporter.__init__(self)

        self.index_template = "index_template.djt"
        self.log_template = "log_template.djt"
        self.output_file_extension = ".html"
        self.index_filename = "index.html"

        self.line_templates = {
            "index_link": u"<li><a href=\"%s\">%s</a></li>",
            "text": u"<p>%s</p>",
            "statement": u"<p><span class=\"player\">%s</span>: %s</p>",
            "emote": u"<p>%s</p>",
        }

    def output_text(self, log_entry):
        return self.line_templates["text"] % log_entry["content"]

    def output_statement(self, log_entry):
        return self.line_templates["statement"] % (log_entry["player"],
                                                   log_entry["content"])

    def output_emote(self, log_entry):
        return self.line_templates["emote"] % log_entry["content"]

    def output_file(self, input_filename, output_filename, previous=None, next=None):
        lines = [self.output_entry(entry) for entry
                 in json.load(file(input_filename))]

        output_file = file(output_filename, "w")
        # TODO: also insert date, since there's a tag for it
        output_lines = template.render(self.log_template, {
            "previous": os.path.basename(previous) if previous else None,
            "next": os.path.basename(next) if next else None,
            "content": self.line_separator.join(lines),
        })
        output_file.writelines(output_lines)
        output_file.close()

    def output_directory(self, input_dir, output_dir):
        # TODO: improve index page. Chapter titles? Can probably be manual.
        input_filenames, output_filenames = LogExporter.build_file_lists(
            self, input_dir, output_dir)
        for input_filename, output_dict in zip(input_filenames,
                                               self.links(output_filenames)):
            self.output_file(input_filename, output_dict["current"],
                             previous=output_dict["previous"],
                             next=output_dict["next"])

        self.output_index_file(output_filenames, self.index_filename)

    def output_index_file(self, output_filenames, output_filename):
        link_lines = [self.build_index_link(filename)
                      for filename in output_filenames]

        output_file = file(self.index_filename, "w")
        output_lines = template.render(self.index_template, {
            "content": self.line_separator.join(link_lines),
        })
        output_file.writelines(output_lines)
        output_file.close()

    def build_index_link(self, filename):
        """Create a link for insertion into the HTML index."""
        url = os.path.basename(filename)
        text = re.sub(r"\.\w+$", "", url)
        return self.line_templates["index_link"] % (url, text)


    def links(self, items):
        """A generator which returns a previous/current/next dict for each item;
        'previous' will be None for the first item, and 'next' will be None for
        the last item."""
        if len(items) == 0:
            raise "Empty list passed to links"
        else:
            for n in range(0, len(items)):
                if n == 0:
                    yield {
                        "previous": None,
                        "current": items[n],
                        "next": items[n+1]
                    }
                elif n == len(items) - 1:
                    yield {
                        "previous": items[n-1],
                        "current": items[n],
                        "next": None
                    }
                else:  # standard case
                    yield {
                        "previous": items[n-1],
                        "current": items[n],
                        "next": items[n+1]
                    }
