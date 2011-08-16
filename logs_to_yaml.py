# process OpenRPG HTML-like logs to YAML
import os, re, json
from BeautifulSoup import BeautifulSoup


class LogConverter:
    """Converts lines, files, or entire directories to log data."""

    def __init__(self):
        self.timestamp_pattern = r"^\[.+\d{4}\] : "
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
            <B>(123) Alan</B>: <font color='#800040'>Example sentence.</font><br>
        """
        self.log("Parsing as v1 statement: %s" % line)
        parsed = BeautifulSoup(line)
        # build log entry
        entry = {
            "type": "statement",
            "player": re.sub(r"^\(\d+\) ", "", parsed.b.renderContents()),
            "content": parsed.font.renderContents(),
        }
        return entry

    def statement_v2(self, line):
        """Parses a statement in the following format:
            <B>Alan</B>: <font color='#800040'>Example sentence.</font><br>
        """

        self.log("Parsing as v2 statement: %s" % line)
        parsed = BeautifulSoup(line)
        # build log entry
        entry = {
            "type": "statement",
            "player": parsed.b.renderContents(),
            "content": parsed.font.renderContents(),
        }
        return entry

    def statement_v3(self, line):
        """Parses a statement in the following format:
            <p><b>Alan</b>: Example sentence.</p>
        """

        self.log("Parsing as v3 statement: %s" % line)
        parsed = BeautifulSoup(line)
        player = parsed.b.extract().renderContents()  # also removes <b> tag
        content = re.sub(r"^: ", "", parsed.p.renderContents())

        # build log entry
        entry = {
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

    def process_line(self, line):
        line = self.strip_timestamp(line.strip())
        for pattern, function in self.content_patterns:
            if re.search(pattern, line):
                return function(line)
        self.log("Discarding input line: %s" % line)
        return None  # if nothing matched

    def process_file(self, input_file, output_file):
        self.log("Processing file: %s -> %s" % (input_file, output_file))
        input_lines = file(input_file).readlines()
        output_lines = [self.process_line(line) for line in input_lines]
        output_lines = filter(None, output_lines)  # remove None elements
        json.dump(output_lines, file(output_file, "w"))

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
