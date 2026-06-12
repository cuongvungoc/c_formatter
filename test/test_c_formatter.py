"""Tests and a basic performance check for c_formatter."""

from __future__ import annotations

import sys
import time
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = PROJECT_ROOT / "test" / "fixtures"
sys.path.insert(0, str(PROJECT_ROOT))

from c_formatter import format_c_code, main  # noqa: E402

PERFORMANCE_RESULTS: list[dict[str, float | int | str]] = []


def read_fixture(name: str) -> str:
    """Read a test fixture as UTF-8 text."""

    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


class CFormatterTests(unittest.TestCase):
    """Validate required formatter behavior."""

    def test_formats_normal_c_file_fixture(self) -> None:
        """Format a common C file with functions, loops, and if/else."""

        source = read_fixture("normal_input.c")
        expected = read_fixture("normal_expected.c")

        self.assertEqual(format_c_code(source), expected)

    def test_formats_edge_case_c_file_fixture(self) -> None:
        """Format required edge cases from the project requirements."""

        source = read_fixture("edge_input.c")
        expected = read_fixture("edge_expected.c")

        self.assertEqual(format_c_code(source), expected)

    def test_cli_formats_input_file_to_output_file(self) -> None:
        """Verify CLI reads a C file and writes formatted output."""

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "formatted.c"
            exit_code = main([str(FIXTURE_DIR / "normal_input.c"), "-o", str(output_path)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(output_path.read_text(encoding="utf-8"), read_fixture("normal_expected.c"))

    def test_cli_can_preserve_input_blank_lines(self) -> None:
        """Verify CLI can keep blank lines from the input file."""

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.c"
            output_path = Path(tmpdir) / "formatted.c"
            input_path.write_text("int a(){return 1;}\n\n\nint b(){return 2;}\n", encoding="utf-8")

            exit_code = main([str(input_path), "-o", str(output_path), "--keep-line-breaks"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "int a() {\n    return 1;\n}\n\n\nint b() {\n    return 2;\n}\n",
            )

    def test_cli_can_apply_allman_brace_style(self) -> None:
        """Verify CLI can put opening braces on the next line."""

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.c"
            output_path = Path(tmpdir) / "formatted.c"
            input_path.write_text("int main(){if(x){return 1;}return 0;}\n", encoding="utf-8")

            exit_code = main([str(input_path), "-o", str(output_path), "--brace-style", "allman"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "int main()\n"
                "{\n"
                "    if (x)\n"
                "    {\n"
                "        return 1;\n"
                "    }\n"
                "    return 0;\n"
                "}\n",
            )

    def test_default_compacts_input_blank_lines(self) -> None:
        """Verify default mode does not preserve input blank lines."""

        source = "int a(){return 1;}\n\n\nint b(){return 2;}\n"

        self.assertEqual(
            format_c_code(source),
            "int a() {\n    return 1;\n}\nint b() {\n    return 2;\n}\n",
        )

    def test_preserve_line_breaks_keeps_input_blank_lines(self) -> None:
        """Verify API option preserves blank lines between formatted nodes."""

        source = "#include <stdio.h>\n\nint a(){return 1;}\n\n\nint b(){return 2;}\n"

        self.assertEqual(
            format_c_code(source, preserve_line_breaks=True),
            "#include <stdio.h>\n\nint a() {\n    return 1;\n}\n\n\nint b() {\n    return 2;\n}\n",
        )

    def test_allman_brace_style_puts_opening_braces_on_next_line(self) -> None:
        """Verify API Allman style for functions and control blocks."""

        source = "int main(){if(x){return 1;}else{return 2;}}"

        self.assertEqual(
            format_c_code(source, brace_style="allman"),
            "int main()\n"
            "{\n"
            "    if (x)\n"
            "    {\n"
            "        return 1;\n"
            "    }\n"
            "    else\n"
            "    {\n"
            "        return 2;\n"
            "    }\n"
            "}\n",
        )

    def test_preserve_line_breaks_does_not_add_blank_after_comment(self) -> None:
        """Keep the original single newline between a comment and function."""

        source = (
            "/* Parse action record from JSON string */\n"
            "static action_record_t* parse_action_record(char *msg)\n"
            "{return NULL;}\n"
        )

        self.assertEqual(
            format_c_code(source, preserve_line_breaks=True),
            "/* Parse action record from JSON string */\n"
            "static action_record_t *parse_action_record(char *msg) {\n"
            "    return NULL;\n"
            "}\n",
        )

    def test_formats_control_flow_and_switch(self) -> None:
        """Format nested blocks, if/else, switch labels, and do/while."""

        source = (
            "int main(){if(x){y=1+2;}else if(y){z=3;}else z=4;"
            "switch(z){case 1:y=2;break;default:y=3;}do{x++;}while(x<10);return 0;}"
        )

        formatted = format_c_code(source)

        self.assertIn("if (x) {", formatted)
        self.assertIn("} else if (y) {", formatted)
        self.assertIn("} else z = 4;", formatted)
        self.assertIn("    case 1:", formatted)
        self.assertIn("    default:", formatted)
        self.assertIn("} while (x < 10);", formatted)
        self.assertTrue(formatted.endswith("\n"))

    def test_formats_pointers_and_binary_operators(self) -> None:
        """Distinguish pointer declarations from multiplication expressions."""

        source = "int (*fp)(int,char*);void f(int*x,char ** y){*x=*x+1;y=&x;z=a*b;}"

        formatted = format_c_code(source)

        self.assertIn("int (*fp)(int, char *);", formatted)
        self.assertIn("void f(int *x, char **y) {", formatted)
        self.assertIn("*x = *x + 1;", formatted)
        self.assertIn("y = &x;", formatted)
        self.assertIn("z = a * b;", formatted)

    def test_keeps_simple_initializer_list_inline(self) -> None:
        """Do not split compact initializer lists into standalone blocks."""

        source = "unsigned char server_box_pk[crypto_box_PUBLICKEYBYTES] = {0};"

        self.assertEqual(
            format_c_code(source),
            "unsigned char server_box_pk[crypto_box_PUBLICKEYBYTES] = {0};\n",
        )

    def test_keeps_trailing_block_comment_on_statement_line(self) -> None:
        """Do not move a same-line block comment to its own line."""

        source = "action_record_t *action_record = NULL;  /* parsed action record */"

        self.assertEqual(
            format_c_code(source),
            "action_record_t *action_record = NULL; /* parsed action record */\n",
        )


class CFormatterPerformanceTests(unittest.TestCase):
    """Exercise formatter throughput on a generated C translation unit."""

    def test_generated_source_formats_under_threshold(self) -> None:
        """Format a moderately large generated file within a generous budget."""

        function_count = 1_000
        source = "\n".join(
            f"int f{i}(int*x){{if(*x<{i}){{*x=*x+{i};}}else *x=*x-1;return *x;}}"
            for i in range(function_count)
        )

        started = time.perf_counter()
        formatted = format_c_code(source)
        elapsed = time.perf_counter() - started

        PERFORMANCE_RESULTS.append(
            {
                "name": "generated translation unit",
                "functions": function_count,
                "input_chars": len(source),
                "elapsed_seconds": elapsed,
                "chars_per_second": len(source) / elapsed,
            }
        )
        self.assertLess(elapsed, 5.0)
        self.assertEqual(formatted.count("return *x;"), function_count)


if __name__ == "__main__":
    unittest.main(verbosity=2)
