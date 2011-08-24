# As it says. Really bone-stupid template system that's barely good enough for
# this limited purpose.

def render(template_filename, replacements):
    """Return a list of lines built by reading the template file and, wherever
    the pattern '{{ foo }}' is found, replacing it with replacements['foo'].
    Where the replacement is None, substitutes an empty string."""

    # I can already see the weakness of this approach: if there is no Previous,
    # for instance, we don't want a line at all. Guess we should just drop in an
    # actual templating system; the Django one might do as well as any other.
    input_file = file(template_filename)
    result = []

    for line in input_file:
        if "{{ " in line:
            for key, value in replacements.items():
                tag = "{{ %s }}" % key
                if tag in line:
                    result.append(line.replace(tag, value or ""))
        else:
            result.append(line)

    input_file.close()
    return result
