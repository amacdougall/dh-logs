# process OpenRPG HTML-like logs to YAML
import os, re, json
from BeautifulSoup import BeautifulSoup


class LogArchiver:
    """Converts OpenRPG log lines, files, or entire directories to JSON data."""

    def __init__(self):
        # openRPG timestamp pattern
        self.timestamp_pattern = r"^\[.+\d{4}\] : "

        # openRPG content patterns, through the years
        self.content_patterns = (
            (r"^<[Bb]>\(\d+\) (.+)</[Bb]>: <font", self.statement_v1),
            (r"^<[Bb]>(.+)</[Bb]>: <font", self.statement_v2),
            (r"^<p><b>(.+)</b>: ", self.statement_v3),
            (r"^<font color='#\d{6}'>\*{2} \(\d+\) ", self.emote_v1),
            (r"^<font color='#\d{6}'>\*{2}", self.emote_v2),
            (r"^<p>\*{2} ", self.emote_v3),
        )

        # if present in the first 10 lines, this is a Campfire log
        self.campfire_log_pattern = r"^\s+<title>Campfire"

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
            <B>(123) Alan</B>: <font color='#800040'>Example sentence.</font><br>
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
        self.log("Parsing as v2 emote: %s" % line)
        parsed = BeautifulSoup(line)
        emote = parsed.font.renderContents()  # gives raw innerHTML
        content = re.search("^\*{2} (.+) \*{2}", emote).group(1)
        entry = {
            "type": "emote",
            "content": content,
        }
        return entry

    def emote_v3(self, line):
        self.log("Parsing as v3 emote: %s" % line)
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
        self.log("Discarding input line: %s" % line)
        return None  # if nothing matched

    def is_campfire_log(self, filename):
        """True if campfire_log_pattern is found in the first 10 lines."""
        log_file = file(filename)
        for n in range(0, 9):
            if re.search(campfire_log_pattern, log_file.readline()):
                return true
        return false

    def is_text_log(self, filename):
        """True if filename ends with .txt."""
        return filename.endswith(".txt")

    def process_file(self, input_file, output_file):
        self.log("Processing file: %s -> %s" % (input_file, output_file))

        if is_campfire_log(input_file):
            self.log("Converting from Campfire transcript to JSON...")
            log_entries = process_campfire_log(input_file)
        elif is_text_log(input_file):
            self.log("Converting from text format to JSON...")
            log_entries = process_text_log(input_file)
        else:
            self.log("Converting from OpenRPG log to JSON...")
            log_entries = process_openRPG_log(input_file)

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
        return [{"type": "text", "content": line.strip()} for line
                in file(input_file).readlines() if line != "\n"]
        

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

        input_files = [filename for filename in os.listdir(input_dir)
                       if filename.endswith(".html")]

        for filename in input_files:
            # open a new log file for each input file
            if self.log_file is None or self.log_file.closed:
                self.log_file = file(self.log_filename, "w")

            input_filename = os.path.join(input_dir, filename)
            output_filename = os.path.join(output_dir, filename)
            output_filename = output_filename.replace(".html", ".json")
            self.process_file(input_filename, output_filename)

            self.log_file.close()

