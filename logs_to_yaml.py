# process OpenRPG HTML-like logs to YAML
import os, re, json


class LogConverter:
    """Converts lines, files, or entire directories to log data."""

    def __init__(self):
        self.timestamp_pattern = r"^\[.+\d{4}\] : "
        self.content_patterns = (
            (r"^<[Bb]>\(\d+\) ((\w+)( \w+)*)</[Bb]>: ", self.statement),
            (r"^<font color='#\d{6}'>\*\* ", self.emote),
        )

    def strip_timestamp(self, line):
        return re.sub(self.timestamp_pattern, "", line)

    def statement(self, line):
        return line

    def emote(self, line):
        return line

    def log_entry(self, line):
        """Using content_patterns, attempt each pattern/function mapping in turn
        and return the results of the function for the first pattern found."""
        for pattern, function in self.content_patterns:
            if re.search(pattern, line):
                return function(line)
        return None  # if nothing matched
