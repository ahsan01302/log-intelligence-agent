def parse_log_file(file_path):

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")

    cleaned_lines = []

    for line in lines:
        line = line.strip()

        if line:
            cleaned_lines.append(line)

    return cleaned_lines