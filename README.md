# C Formatter

A small C source formatter written in Python. It provides both a command-line formatter and a Flask web UI for formatting pasted C code.

The formatter is intentionally lightweight. It does not implement the full C grammar, but it uses a mini compiler-style pipeline with a lexer, lightweight parser, and formatter so common C files can be cleaned up consistently.

## Key Features

- Formats C source from a `.c` / `.h` file path or a raw source string.
- Writes formatted output to stdout or to a file.
- Uses 4 spaces per indentation level.
- Supports K&R and Allman brace styles.
- Optional preservation of input blank lines.
- Preserves string literals, character literals, comments, and preprocessor directives.
- Handles common constructs:
  - functions
  - `if` / `else`
  - `for`, `while`, `do while`
  - `switch`, `case`, `default`
  - simple initializer lists such as `{0}`
  - basic pointer and function pointer declarations
- Includes a Flask web app on port `8888`.
- Includes unit tests and a professional test report runner.

## Project Layout

```text
c_formatter.py          Command-line formatter and formatting library
app.py                  Flask web application
requirements.txt        Python package dependencies
test/                   Unit tests and test runner
test/fixtures/          C input and expected-output fixtures
```

## Requirements

- Python 3.10+
- Flask for the web app

## Install

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

If you do not activate the virtual environment, use `.venv/bin/python` and `.venv/bin/pip` in the commands below.

## CLI Usage

Format a file and print to stdout:

```bash
python3 c_formatter.py input.c
```

Format a file and write to another file:

```bash
python3 c_formatter.py input.c -o output.c
```

Format a raw source string:

```bash
python3 c_formatter.py 'int main(){return 0;}'
```

Preserve input blank lines:

```bash
python3 c_formatter.py input.c -o output.c --keep-line-breaks
```

Short form:

```bash
python3 c_formatter.py input.c -o output.c -k
```

Use K&R brace style, the default:

```bash
python3 c_formatter.py input.c -o output.c --brace-style kr
```

Use Allman brace style:

```bash
python3 c_formatter.py input.c -o output.c --brace-style allman
```

## Brace Styles

K&R style keeps the opening brace on the same line:

```c
if (x) {
    return 1;
}
```

Allman style puts the opening brace on the next line:

```c
if (x)
{
    return 1;
}
```

## Web App

Run the Flask app:

```bash
python3 app.py
```

Or with the local virtual environment:

```bash
.venv/bin/python app.py
```

Open:

```text
http://127.0.0.1:8888
```

The web page provides:

- Input textarea for pasted C code
- Output textarea for formatted C code
- `Keep input blank lines` checkbox
- `Allman brace style` checkbox
- `Format Code` button

Health check:

```bash
curl http://127.0.0.1:8888/health
```

Expected response:

```json
{"status":"ok"}
```

## Run Tests

Run the standard unittest suite:

```bash
python3 -m unittest discover -s test -v
```

Run the custom report runner:

```bash
python3 test/run_tests.py
```

With the virtual environment:

```bash
.venv/bin/python -m unittest discover -s test -v
.venv/bin/python test/run_tests.py
```

## Library Usage

You can call the formatter directly from Python:

```python
from c_formatter import format_c_code

formatted = format_c_code(
    "int main(){return 0;}",
    preserve_line_breaks=False,
    brace_style="kr",
)
```

Allman example:

```python
formatted = format_c_code(
    "int main(){return 0;}",
    brace_style="allman",
)
```

## Notes And Limitations

This is a simplified formatter, not a full replacement for `clang-format`. It is designed for common C formatting tasks and project-specific experimentation. Complex macro-heavy code, unusual declarations, and advanced C grammar may still need manual review.
