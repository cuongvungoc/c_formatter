"""Flask web app for formatting pasted C source code."""

from __future__ import annotations

from flask import Flask, request, render_template

from c_formatter import BRACE_STYLE_ALLMAN, BRACE_STYLE_KR, format_c_code


app = Flask(__name__)


INDEX_PAGE = "index.html"


@app.route("/", methods=["GET", "POST"])
def index() -> str:
    """Render the formatter UI and handle form submissions."""

    source = ""
    formatted = ""
    error = ""
    keep_line_breaks = False
    allman_braces = False

    if request.method == "POST":
        source = request.form.get("source", "")
        keep_line_breaks = request.form.get("keep_line_breaks") == "1"
        allman_braces = request.form.get("allman_braces") == "1"
        brace_style = BRACE_STYLE_ALLMAN if allman_braces else BRACE_STYLE_KR
        try:
            formatted = format_c_code(
                source,
                preserve_line_breaks=keep_line_breaks,
                brace_style=brace_style,
            )
        except Exception as exc:  # pragma: no cover - defensive UI boundary.
            error = f"Formatter error: {exc}"

    return render_template(
        INDEX_PAGE,
        input_source=source,
        formatted=formatted,
        keep_line_breaks=keep_line_breaks,
        allman_braces=allman_braces,
        error=error,
    )


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    """Return a simple health response for deployment checks."""

    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8888)
