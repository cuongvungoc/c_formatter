"""Flask web app for formatting pasted C source code."""

from __future__ import annotations

from flask import Flask, render_template_string, request

from c_formatter import format_c_code


app = Flask(__name__)


PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>C Formatter</title>
    <style>
        :root {
            color-scheme: light;
            --bg: #f4f6f8;
            --surface: #ffffff;
            --surface-2: #eef2f6;
            --text: #202833;
            --muted: #5d6978;
            --border: #cfd7e2;
            --accent: #0b6bcb;
            --accent-hover: #0759ab;
            --danger: #b42318;
            --shadow: 0 12px 30px rgba(31, 42, 55, 0.08);
        }

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            min-height: 100vh;
            background: var(--bg);
            color: var(--text);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .app-shell {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            border-bottom: 1px solid var(--border);
            background: var(--surface);
        }

        .header-inner {
            max-width: 1440px;
            margin: 0 auto;
            padding: 18px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
        }

        h1 {
            margin: 0;
            font-size: 22px;
            line-height: 1.2;
            font-weight: 700;
            letter-spacing: 0;
        }

        .status {
            min-height: 20px;
            color: var(--muted);
            font-size: 14px;
        }

        main {
            width: 100%;
            max-width: 1440px;
            margin: 0 auto;
            padding: 24px;
            flex: 1;
        }

        form {
            display: grid;
            grid-template-rows: auto minmax(520px, 1fr);
            gap: 16px;
            min-height: calc(100vh - 116px);
        }

        .toolbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            padding: 14px 16px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            box-shadow: var(--shadow);
        }

        .option {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            color: var(--text);
            font-size: 15px;
            cursor: pointer;
            user-select: none;
        }

        input[type="checkbox"] {
            width: 18px;
            height: 18px;
            accent-color: var(--accent);
        }

        button {
            min-height: 40px;
            padding: 0 18px;
            border: 0;
            border-radius: 8px;
            background: var(--accent);
            color: #ffffff;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
        }

        button:hover {
            background: var(--accent-hover);
        }

        .editor-grid {
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
            gap: 16px;
            min-height: 0;
        }

        .editor-pane {
            display: grid;
            grid-template-rows: auto minmax(0, 1fr);
            min-height: 0;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            box-shadow: var(--shadow);
            overflow: hidden;
        }

        .pane-header {
            padding: 12px 14px;
            border-bottom: 1px solid var(--border);
            background: var(--surface-2);
            font-size: 14px;
            font-weight: 700;
            color: var(--text);
        }

        textarea {
            width: 100%;
            min-height: 100%;
            resize: none;
            border: 0;
            outline: 0;
            padding: 16px;
            color: #17202c;
            background: #ffffff;
            font: 14px/1.55 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
            tab-size: 4;
        }

        textarea[readonly] {
            background: #fbfcfe;
        }

        .error {
            color: var(--danger);
            font-weight: 700;
        }

        @media (max-width: 900px) {
            .header-inner,
            main {
                padding-left: 16px;
                padding-right: 16px;
            }

            form {
                grid-template-rows: auto auto;
            }

            .toolbar {
                align-items: stretch;
                flex-direction: column;
            }

            button {
                width: 100%;
            }

            .editor-grid {
                grid-template-columns: 1fr;
            }

            .editor-pane {
                min-height: 420px;
            }
        }
    </style>
</head>
<body>
    <div class="app-shell">
        <header>
            <div class="header-inner">
                <h1>C Formatter</h1>
                <div class="status{% if error %} error{% endif %}">
                    {% if error %}{{ error }}{% elif formatted %}Formatted successfully{% else %}Ready{% endif %}
                </div>
            </div>
        </header>
        <main>
            <form method="post">
                <div class="toolbar">
                    <label class="option">
                        <input type="checkbox" name="keep_line_breaks" value="1"{% if keep_line_breaks %} checked{% endif %}>
                        Keep input blank lines
                    </label>
                    <button type="submit">Format Code</button>
                </div>
                <div class="editor-grid">
                    <section class="editor-pane" aria-labelledby="input-label">
                        <div class="pane-header" id="input-label">Input</div>
                        <textarea name="source" spellcheck="false" autofocus>{{ input_source }}</textarea>
                    </section>
                    <section class="editor-pane" aria-labelledby="output-label">
                        <div class="pane-header" id="output-label">Output</div>
                        <textarea readonly spellcheck="false">{{ formatted }}</textarea>
                    </section>
                </div>
            </form>
        </main>
    </div>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index() -> str:
    """Render the formatter UI and handle form submissions."""

    source = ""
    formatted = ""
    error = ""
    keep_line_breaks = False

    if request.method == "POST":
        source = request.form.get("source", "")
        keep_line_breaks = request.form.get("keep_line_breaks") == "1"
        try:
            formatted = format_c_code(source, preserve_line_breaks=keep_line_breaks)
        except Exception as exc:  # pragma: no cover - defensive UI boundary.
            error = f"Formatter error: {exc}"

    return render_template_string(
        PAGE_TEMPLATE,
        input_source=source,
        formatted=formatted,
        keep_line_breaks=keep_line_breaks,
        error=error,
    )


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    """Return a simple health response for deployment checks."""

    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8888)
