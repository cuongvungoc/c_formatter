#!/usr/bin/env python3
"""A small C source formatter implemented as a lexer/parser/formatter pipeline."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterable


INDENT = " " * 4
BRACE_STYLE_KR = "kr"
BRACE_STYLE_ALLMAN = "allman"
BRACE_STYLES = {BRACE_STYLE_KR, BRACE_STYLE_ALLMAN}


class TokenKind(Enum):
    """Token categories understood by the formatter."""

    KEYWORD = auto()
    IDENTIFIER = auto()
    NUMBER = auto()
    STRING = auto()
    CHAR = auto()
    OPERATOR = auto()
    PUNCTUATION = auto()
    COMMENT = auto()
    PREPROCESSOR = auto()
    NEWLINE = auto()
    EOF = auto()


@dataclass(frozen=True)
class Token:
    """A lexical token with its original source location."""

    kind: TokenKind
    value: str
    line: int
    column: int


@dataclass
class ProgramNode:
    """Root AST node containing top-level structured items."""

    children: list["Node"]


@dataclass
class BlockNode:
    """A block with optional leading header tokens and nested children."""

    header: list[Token]
    children: list["Node"]


@dataclass
class StatementNode:
    """A flat statement or declaration represented by its token sequence."""

    tokens: list[Token]


@dataclass
class CommentNode:
    """A standalone comment that should be emitted without changing content."""

    token: Token


@dataclass
class PreprocessorNode:
    """A preprocessor directive that should be emitted exactly as read."""

    token: Token


@dataclass
class BlankLineNode:
    """One or more preserved blank lines from the original source."""

    count: int = 1


Node = ProgramNode | BlockNode | StatementNode | CommentNode | PreprocessorNode | BlankLineNode


KEYWORDS = {
    "auto",
    "break",
    "case",
    "char",
    "const",
    "continue",
    "default",
    "do",
    "double",
    "else",
    "enum",
    "extern",
    "float",
    "for",
    "goto",
    "if",
    "inline",
    "int",
    "long",
    "register",
    "restrict",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "struct",
    "switch",
    "typedef",
    "union",
    "unsigned",
    "void",
    "volatile",
    "while",
    "_Bool",
    "_Complex",
    "_Imaginary",
}

CONTROL_KEYWORDS = {"if", "for", "while", "switch"}
TYPELIKE_KEYWORDS = {
    "auto",
    "char",
    "const",
    "double",
    "enum",
    "extern",
    "float",
    "inline",
    "int",
    "long",
    "register",
    "restrict",
    "short",
    "signed",
    "static",
    "struct",
    "typedef",
    "union",
    "unsigned",
    "void",
    "volatile",
    "_Bool",
    "_Complex",
    "_Imaginary",
}

MULTI_OPERATORS = [
    "<<=",
    ">>=",
    "...",
    "++",
    "--",
    "->",
    "==",
    "!=",
    "<=",
    ">=",
    "&&",
    "||",
    "+=",
    "-=",
    "*=",
    "/=",
    "%=",
    "&=",
    "|=",
    "^=",
    "<<",
    ">>",
    "##",
]
SINGLE_OPERATORS = set("=+-*/%<>!&|^~?:.")
PUNCTUATION = set("()[]{};,")
BINARY_OPERATORS = {
    "=",
    "+",
    "-",
    "*",
    "/",
    "%",
    "<",
    ">",
    "==",
    "!=",
    "<=",
    ">=",
    "&&",
    "||",
    "+=",
    "-=",
    "*=",
    "/=",
    "%=",
    "&=",
    "|=",
    "^=",
    "<<",
    ">>",
    "<<=",
    ">>=",
    "&",
    "|",
    "^",
}
UNARY_OPERATORS = {"!", "~", "++", "--"}


class Lexer:
    """Converts C source text into tokens while preserving comments and strings."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.length = len(source)
        self.index = 0
        self.line = 1
        self.column = 1
        self.at_line_start = True
        self.only_space_on_line = True

    def tokenize(self) -> list[Token]:
        """Tokenize the entire source string and append an EOF sentinel."""

        tokens: list[Token] = []
        while self.index < self.length:
            char = self._peek()

            if char in " \t\r\f\v":
                self._advance()
                continue

            if char == "\n":
                tokens.append(self._make_token(TokenKind.NEWLINE, "\n"))
                self._advance()
                self.at_line_start = True
                self.only_space_on_line = True
                continue

            if char == "#" and self.only_space_on_line:
                tokens.append(self._read_preprocessor())
                continue

            if char == "/" and self._peek(1) == "/":
                tokens.append(self._read_line_comment())
                continue

            if char == "/" and self._peek(1) == "*":
                tokens.append(self._read_block_comment())
                continue

            if char == '"':
                tokens.append(self._read_quoted(TokenKind.STRING, '"'))
                continue

            if char == "'":
                tokens.append(self._read_quoted(TokenKind.CHAR, "'"))
                continue

            if char.isalpha() or char == "_":
                tokens.append(self._read_identifier())
                continue

            if char.isdigit():
                tokens.append(self._read_number())
                continue

            op = self._match_operator()
            if op:
                tokens.append(self._consume_token(TokenKind.OPERATOR, op))
                continue

            if char in PUNCTUATION:
                tokens.append(self._consume_token(TokenKind.PUNCTUATION, char))
                continue

            tokens.append(self._consume_token(TokenKind.PUNCTUATION, char))

        tokens.append(Token(TokenKind.EOF, "", self.line, self.column))
        return tokens

    def _peek(self, offset: int = 0) -> str:
        """Return a character at an offset without consuming it."""

        pos = self.index + offset
        if pos >= self.length:
            return ""
        return self.source[pos]

    def _advance(self) -> str:
        """Consume and return one character while updating source position."""

        char = self.source[self.index]
        self.index += 1
        if char == "\n":
            self.line += 1
            self.column = 1
            self.at_line_start = True
            self.only_space_on_line = True
        else:
            self.column += 1
            if char not in " \t\r\f\v":
                self.at_line_start = False
                self.only_space_on_line = False
        return char

    def _make_token(self, kind: TokenKind, value: str) -> Token:
        """Create a token at the current source position."""

        return Token(kind, value, self.line, self.column)

    def _consume_token(self, kind: TokenKind, value: str) -> Token:
        """Create a token and consume exactly its value from the source."""

        token = self._make_token(kind, value)
        for _ in value:
            self._advance()
        return token

    def _read_preprocessor(self) -> Token:
        """Read a preprocessor directive, including backslash continuations."""

        start_line, start_col = self.line, self.column
        value: list[str] = []
        continued = True
        while self.index < self.length and continued:
            continued = False
            while self.index < self.length:
                char = self._advance()
                if char == "\n":
                    break
                value.append(char)
            text = "".join(value).rstrip()
            if text.endswith("\\") and self.index < self.length:
                value.append("\n")
                continued = True
        return Token(TokenKind.PREPROCESSOR, "".join(value).rstrip(), start_line, start_col)

    def _read_line_comment(self) -> Token:
        """Read a // comment without consuming the terminating newline."""

        start_line, start_col = self.line, self.column
        value: list[str] = []
        while self.index < self.length and self._peek() != "\n":
            value.append(self._advance())
        return Token(TokenKind.COMMENT, "".join(value), start_line, start_col)

    def _read_block_comment(self) -> Token:
        """Read a possibly multi-line /* */ comment as one token."""

        start_line, start_col = self.line, self.column
        value: list[str] = []
        while self.index < self.length:
            char = self._advance()
            value.append(char)
            if char == "*" and self._peek() == "/":
                value.append(self._advance())
                break
        return Token(TokenKind.COMMENT, "".join(value), start_line, start_col)

    def _read_quoted(self, kind: TokenKind, quote: str) -> Token:
        """Read a string or character literal, honoring escaped characters."""

        start_line, start_col = self.line, self.column
        value = [self._advance()]
        escaped = False
        while self.index < self.length:
            char = self._advance()
            value.append(char)
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == quote:
                break
        return Token(kind, "".join(value), start_line, start_col)

    def _read_identifier(self) -> Token:
        """Read an identifier or keyword token."""

        start_line, start_col = self.line, self.column
        value: list[str] = []
        while self._peek().isalnum() or self._peek() == "_":
            value.append(self._advance())
        text = "".join(value)
        kind = TokenKind.KEYWORD if text in KEYWORDS else TokenKind.IDENTIFIER
        return Token(kind, text, start_line, start_col)

    def _read_number(self) -> Token:
        """Read a C-style numeric literal using permissive scanning."""

        start_line, start_col = self.line, self.column
        value: list[str] = []
        while True:
            char = self._peek()
            prev = value[-1] if value else ""
            if char.isalnum() or char in "._":
                value.append(self._advance())
            elif char in "+-" and prev in "eEpP":
                value.append(self._advance())
            else:
                break
        return Token(TokenKind.NUMBER, "".join(value), start_line, start_col)

    def _match_operator(self) -> str | None:
        """Return the longest operator matching the current source position."""

        for op in MULTI_OPERATORS:
            if self.source.startswith(op, self.index):
                return op
        if self._peek() in SINGLE_OPERATORS:
            return self._peek()
        return None


class Parser:
    """Builds a lightweight tree of blocks, statements, comments, and directives."""

    def __init__(self, tokens: list[Token], preserve_line_breaks: bool = False) -> None:
        self.tokens = tokens
        self.index = 0
        self.preserve_line_breaks = preserve_line_breaks

    def parse(self) -> ProgramNode:
        """Parse all tokens into a ProgramNode."""

        return ProgramNode(self._parse_sequence(stop_at_closing_brace=False))

    def _parse_sequence(self, stop_at_closing_brace: bool) -> list[Node]:
        """Parse nodes until EOF or a matching closing brace is found."""

        nodes: list[Node] = []
        current: list[Token] = []
        paren_depth = 0
        bracket_depth = 0
        pending_newlines = 0

        while not self._is_at_end():
            token = self._advance()

            if token.kind == TokenKind.NEWLINE:
                if not current:
                    pending_newlines += 1
                continue

            if token.kind == TokenKind.PREPROCESSOR:
                self._flush_statement(nodes, current)
                current.clear()
                self._append_node(nodes, PreprocessorNode(token), pending_newlines)
                pending_newlines = 0
                continue

            if token.kind == TokenKind.COMMENT and not current:
                self._append_node(nodes, CommentNode(token), pending_newlines)
                pending_newlines = 0
                continue

            if token.value == "{":
                if self._is_initializer_brace(current):
                    current.append(token)
                    current.extend(self._read_balanced_initializer())
                    continue
                header = current[:]
                current.clear()
                paren_depth = 0
                bracket_depth = 0
                children = self._parse_sequence(stop_at_closing_brace=True)
                self._append_node(nodes, BlockNode(header, children), pending_newlines)
                pending_newlines = 0
                continue

            if token.value == "}":
                self._flush_statement(nodes, current)
                current.clear()
                paren_depth = 0
                bracket_depth = 0
                if stop_at_closing_brace:
                    return nodes
                self._append_node(nodes, StatementNode([token]), pending_newlines)
                pending_newlines = 0
                continue

            current.append(token)
            if token.value == "(":
                paren_depth += 1
            elif token.value == ")" and paren_depth:
                paren_depth -= 1
            elif token.value == "[":
                bracket_depth += 1
            elif token.value == "]" and bracket_depth:
                bracket_depth -= 1

            if token.value == ":" and paren_depth == 0 and bracket_depth == 0 and self._is_label_buffer(current):
                self._flush_statement(nodes, current, pending_newlines)
                pending_newlines = 0
                current.clear()
                continue

            if token.value == ";" and paren_depth == 0 and bracket_depth == 0:
                trailing_comment = self._consume_same_line_comment(token)
                if trailing_comment:
                    current.append(trailing_comment)
                self._flush_statement(nodes, current, pending_newlines)
                pending_newlines = 0
                current.clear()

        self._flush_statement(nodes, current, pending_newlines)
        return nodes

    def _advance(self) -> Token:
        """Consume and return the next token."""

        token = self.tokens[self.index]
        self.index += 1
        return token

    def _is_at_end(self) -> bool:
        """Return true when the parser reaches EOF."""

        return self.index >= len(self.tokens) or self.tokens[self.index].kind == TokenKind.EOF

    def _flush_statement(self, nodes: list[Node], tokens: list[Token], pending_newlines: int = 0) -> None:
        """Append a statement node if the token buffer has real content."""

        filtered = [token for token in tokens if token.kind != TokenKind.NEWLINE]
        if filtered:
            self._append_node(nodes, StatementNode(filtered), pending_newlines)

    def _append_node(self, nodes: list[Node], node: Node, pending_newlines: int) -> None:
        """Append a node and optional preserved blank lines before it."""

        if self.preserve_line_breaks and nodes and not self._must_attach_to_previous(nodes[-1], node):
            blank_count = self._blank_lines_before(nodes[-1], pending_newlines)
            if blank_count > 0:
                nodes.append(BlankLineNode(blank_count))
        nodes.append(node)

    def _blank_lines_before(self, previous_node: Node, pending_newlines: int) -> int:
        """Convert pending newline tokens into blank lines between nodes."""

        if pending_newlines <= 0:
            return 0
        if isinstance(previous_node, PreprocessorNode):
            return pending_newlines
        return pending_newlines - 1

    def _must_attach_to_previous(self, previous_node: Node, node: Node) -> bool:
        """Return true when C syntax requires two nodes to remain adjacent."""

        if not isinstance(previous_node, BlockNode):
            return False
        if isinstance(node, BlockNode) and self._node_starts_with(node, "else"):
            return True
        if isinstance(node, StatementNode) and self._node_starts_with(node, "else"):
            return True
        if isinstance(node, StatementNode) and self._node_starts_with(previous_node, "do"):
            return self._node_starts_with(node, "while")
        return False

    def _node_starts_with(self, node: Node, value: str) -> bool:
        """Return true when a block header or statement starts with a value."""

        if isinstance(node, BlockNode):
            return bool(node.header) and node.header[0].value == value
        if isinstance(node, StatementNode):
            return bool(node.tokens) and node.tokens[0].value == value
        return False

    def _is_label_buffer(self, tokens: list[Token]) -> bool:
        """Return true when the current token buffer is a C label."""

        if not tokens or tokens[-1].value != ":":
            return False
        return tokens[0].value in {"case", "default"} or len(tokens) == 2

    def _is_initializer_brace(self, tokens: list[Token]) -> bool:
        """Return true when an opening brace belongs to an initializer list."""

        return bool(tokens) and tokens[-1].value == "="

    def _read_balanced_initializer(self) -> list[Token]:
        """Read tokens through the matching initializer closing brace."""

        tokens: list[Token] = []
        depth = 1
        while not self._is_at_end() and depth:
            token = self._advance()
            if token.kind == TokenKind.NEWLINE:
                continue
            tokens.append(token)
            if token.value == "{":
                depth += 1
            elif token.value == "}":
                depth -= 1
        return tokens

    def _consume_same_line_comment(self, token: Token) -> Token | None:
        """Consume a trailing comment that appears on the same line as a token."""

        if self._is_at_end():
            return None
        next_token = self.tokens[self.index]
        if next_token.kind == TokenKind.COMMENT and next_token.line == token.line:
            return self._advance()
        return None


class Formatter:
    """Formats the parsed C token tree with simple K&R-style rules."""

    def __init__(self, indent_unit: str = INDENT, brace_style: str = BRACE_STYLE_KR) -> None:
        self.indent_unit = indent_unit
        self.brace_style = brace_style

    def format(self, program: ProgramNode) -> str:
        """Format a complete program and return a newline-terminated string."""

        lines = self._format_nodes(program.children, 0)
        while lines and lines[-1] == "":
            lines.pop()
        return "\n".join(lines) + ("\n" if lines else "")

    def _format_nodes(self, nodes: Iterable[Node], indent: int) -> list[str]:
        """Format a sequence of AST nodes at a given indentation level."""

        node_list = list(nodes)
        lines: list[str] = []
        index = 0
        while index < len(node_list):
            node = node_list[index]
            if isinstance(node, PreprocessorNode):
                lines.extend(self._format_preprocessor(node))
                index += 1
                continue

            if isinstance(node, BlankLineNode):
                lines.extend("" for _ in range(node.count))
            elif isinstance(node, CommentNode):
                lines.extend(self._format_comment(node.token, indent))
            elif isinstance(node, StatementNode):
                lines.extend(self._format_statement(node.tokens, indent))
            elif isinstance(node, BlockNode):
                block_lines = self._format_block(node, indent)
                index += 1
                while index < len(node_list):
                    next_node = node_list[index]
                    if (
                        self.brace_style == BRACE_STYLE_KR
                        and isinstance(next_node, BlockNode)
                        and self._starts_with(next_node.header, "else")
                    ):
                        next_lines = self._format_block(next_node, indent)
                        block_lines[-1] = f"{block_lines[-1]} {next_lines[0].lstrip()}"
                        block_lines.extend(next_lines[1:])
                        index += 1
                        continue
                    if (
                        self.brace_style == BRACE_STYLE_KR
                        and isinstance(next_node, StatementNode)
                        and self._starts_with(next_node.tokens, "else")
                    ):
                        next_lines = self._format_statement(next_node.tokens, indent)
                        block_lines[-1] = f"{block_lines[-1]} {next_lines[0].lstrip()}"
                        index += 1
                        break
                    if isinstance(next_node, StatementNode) and self._starts_with(node.header, "do"):
                        if self._starts_with(next_node.tokens, "while"):
                            next_lines = self._format_statement(next_node.tokens, indent)
                            block_lines[-1] = f"{block_lines[-1]} {next_lines[0].lstrip()}"
                            index += 1
                    break
                lines.extend(block_lines)
                continue
            index += 1
        return lines

    def _format_preprocessor(self, node: PreprocessorNode) -> list[str]:
        """Emit preprocessor directives exactly, at column zero."""

        return node.token.value.splitlines() or [node.token.value]

    def _format_comment(self, token: Token, indent: int) -> list[str]:
        """Emit a standalone comment without altering its internal text."""

        prefix = self.indent_unit * indent
        lines = token.value.splitlines()
        if not lines:
            return [prefix]
        return [prefix + line if line else prefix for line in lines]

    def _format_block(self, node: BlockNode, indent: int) -> list[str]:
        """Format a braced block with the configured opening-brace style."""

        prefix = self.indent_unit * indent
        header = self._format_tokens(node.header).strip()
        if self.brace_style == BRACE_STYLE_ALLMAN and header:
            lines = [f"{prefix}{header}", f"{prefix}{{"]
        else:
            open_line = f"{prefix}{header} {{" if header else f"{prefix}{{"
            lines = [open_line.rstrip()]
        lines.extend(self._format_nodes(node.children, indent + 1))
        lines.append(f"{prefix}}}")
        return lines

    def _format_statement(self, tokens: list[Token], indent: int) -> list[str]:
        """Format a flat statement, including labels and one-line controls."""

        if len(tokens) == 1 and tokens[0].kind == TokenKind.COMMENT:
            return self._format_comment(tokens[0], indent)

        if self._is_label(tokens):
            label_indent = max(indent - 1, 0) if tokens[0].value in {"case", "default"} else 0
            return [self.indent_unit * label_indent + self._format_tokens(tokens).strip()]

        if tokens and tokens[-1].value == ";":
            lead, trailing_comments = self._split_trailing_comments(tokens)
            text = self._format_tokens(lead).strip()
            if not text.endswith(";"):
                text += ";"
            if trailing_comments:
                text += " " + " ".join(comment.value for comment in trailing_comments)
            return [self.indent_unit * indent + text]

        return [self.indent_unit * indent + self._format_tokens(tokens).strip()]

    def _starts_with(self, tokens: list[Token], value: str) -> bool:
        """Return true when a token list starts with a specific token value."""

        return bool(tokens) and tokens[0].value == value

    def _split_trailing_comments(self, tokens: list[Token]) -> tuple[list[Token], list[Token]]:
        """Separate final comment tokens from a statement token list."""

        split_at = len(tokens)
        while split_at > 0 and tokens[split_at - 1].kind == TokenKind.COMMENT:
            split_at -= 1
        return tokens[:split_at], tokens[split_at:]

    def _is_label(self, tokens: list[Token]) -> bool:
        """Detect case/default/goto labels so they align one level outward."""

        if len(tokens) >= 2 and tokens[1].value == ":":
            return True
        return len(tokens) >= 3 and tokens[0].value == "case" and tokens[-1].value == ":"

    def _format_tokens(self, tokens: list[Token]) -> str:
        """Format a token sequence by applying local spacing rules."""

        result: list[str] = []
        prev_prev: Token | None = None
        prev: Token | None = None
        paren_stack: list[str] = []

        for i, token in enumerate(tokens):
            if token.kind == TokenKind.NEWLINE:
                continue

            if result and self._needs_space(prev_prev, prev, token, self._next_token(tokens, i), paren_stack):
                result.append(" ")

            result.append(token.value)

            if token.value == "(":
                paren_stack.append(prev.value if prev else "")
            elif token.value == ")" and paren_stack:
                paren_stack.pop()

            prev_prev = prev
            prev = token

        text = "".join(result)
        return " ".join(text.split())

    def _next_token(self, tokens: list[Token], index: int) -> Token | None:
        """Return the next non-newline token after an index."""

        for token in tokens[index + 1 :]:
            if token.kind != TokenKind.NEWLINE:
                return token
        return None

    def _needs_space(
        self,
        prev_prev: Token | None,
        prev: Token | None,
        current: Token,
        next_token: Token | None,
        paren_stack: list[str],
    ) -> bool:
        """Decide whether to insert a space before the current token."""

        if prev is None:
            return False

        if current.kind == TokenKind.COMMENT or prev.kind == TokenKind.COMMENT:
            return True

        if current.value in {
            ")",
            "]",
            "}",
            ";",
            ",",
        }:
            return False

        if current.value == ":":
            return False

        if prev.value in {"(", "[", "{", "."}:
            return False

        if current.value in {"(", "["}:
            if prev.value in CONTROL_KEYWORDS:
                return True
            if current.value == "(" and prev.value in TYPELIKE_KEYWORDS and next_token and next_token.value == "*":
                return True
            return False

        if prev.value == ",":
            return True

        if prev.value == ";":
            return True

        if prev.value == ":":
            return True

        if current.value == "->" or prev.value == "->":
            return False

        if current.value in {"++", "--"} or prev.value in {"++", "--"}:
            return False

        if current.value in {"*", "&"} and prev.value in {"*", "&"}:
            if self._operator_before_word_is_unary(prev_prev):
                return False

        if current.value in BINARY_OPERATORS or prev.value in BINARY_OPERATORS:
            if self._is_unary_context(prev_prev, prev, current, next_token, paren_stack):
                if current.value in {"*", "&", "+", "-"} and prev.value in {"return", "case"}:
                    return True
                if current.value in {"*", "&"} and prev.value in TYPELIKE_KEYWORDS:
                    return True
                if current.value in {"*", "&"} and prev.value in BINARY_OPERATORS:
                    return True
                return False
            return True

        if current.value in UNARY_OPERATORS or prev.value in UNARY_OPERATORS:
            return False

        if self._is_wordlike(prev) and self._is_wordlike(current):
            return True

        if prev.value == ")" and self._is_wordlike(current):
            return True

        if self._is_wordlike(prev) and current.value == "*":
            return True

        return False

    def _is_unary_context(
        self,
        prev_prev: Token | None,
        prev: Token,
        current: Token,
        next_token: Token | None,
        paren_stack: list[str],
    ) -> bool:
        """Identify common unary pointer, address, sign, and dereference uses."""

        if current.value not in {"*", "&", "+", "-"} and prev.value not in {"*", "&", "+", "-"}:
            return False

        if current.value in {"*", "&"} and prev.value in TYPELIKE_KEYWORDS:
            return True

        if current.value in {"+", "-"} and prev.value in {"(", "[", ",", "=", "return", "case", ":"}:
            return True

        if current.value in {"*", "&"} and prev.value in {"(", "[", ",", "=", "return", "case", ":"}:
            return True

        if prev.value in {"*", "&"} and current.kind in {
            TokenKind.IDENTIFIER,
            TokenKind.KEYWORD,
            TokenKind.NUMBER,
            TokenKind.STRING,
            TokenKind.CHAR,
        }:
            if current.kind == TokenKind.IDENTIFIER and current.value.startswith("_"):
                return False
            return self._operator_before_word_is_unary(prev_prev)

        if prev.value in {"*", "&"}:
            return self._operator_before_word_is_unary(prev_prev)

        if prev.value in {"+", "-"} and current.kind in {
            TokenKind.IDENTIFIER,
            TokenKind.NUMBER,
        }:
            return self._operator_before_word_is_unary(prev_prev)

        if paren_stack and paren_stack[-1] in {"sizeof"} and current.value in {"*", "&"}:
            return True

        return False

    def _operator_before_word_is_unary(self, prev_prev: Token | None) -> bool:
        """Classify a previous * or & as unary using the token before it."""

        if prev_prev is None:
            return True
        if prev_prev.value in TYPELIKE_KEYWORDS:
            return True
        if prev_prev.kind == TokenKind.IDENTIFIER and prev_prev.value.endswith("_t"):
            return True
        if prev_prev.value in {"(", "[", ",", "=", "return", "case", ":", "*", "&"}:
            return True
        return False

    def _is_wordlike(self, token: Token) -> bool:
        """Return whether a token should be spaced like an identifier word."""

        return token.kind in {
            TokenKind.KEYWORD,
            TokenKind.IDENTIFIER,
            TokenKind.NUMBER,
            TokenKind.STRING,
            TokenKind.CHAR,
        }


def format_c_code(
    source: str,
    preserve_line_breaks: bool = False,
    brace_style: str = BRACE_STYLE_KR,
) -> str:
    """Format raw C source code using the full pipeline."""

    if brace_style not in BRACE_STYLES:
        raise ValueError(f"unsupported brace style: {brace_style}")
    tokens = Lexer(source).tokenize()
    program = Parser(tokens, preserve_line_breaks=preserve_line_breaks).parse()
    return Formatter(brace_style=brace_style).format(program)


def read_input(value: str) -> str:
    """Read input as a filesystem path if it exists, otherwise as raw source."""

    if os.path.exists(value):
        with open(value, "r", encoding="utf-8") as source_file:
            return source_file.read()
    return value


def write_output(formatted: str, output_path: str | None) -> None:
    """Write formatted source to a file or stdout."""

    if output_path:
        with open(output_path, "w", encoding="utf-8") as output_file:
            output_file.write(formatted)
    else:
        sys.stdout.write(formatted)


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for the formatter."""

    parser = argparse.ArgumentParser(description="Format C source code.")
    parser.add_argument("input", help="Path to a .c/.h file or a raw C source string.")
    parser.add_argument("-o", "--output", help="Write formatted C code to this path.")
    parser.add_argument(
        "-k",
        "--keep-line-breaks",
        action="store_true",
        help="Preserve blank lines from the input file.",
    )
    parser.add_argument(
        "--brace-style",
        choices=sorted(BRACE_STYLES),
        default=BRACE_STYLE_KR,
        help="Opening brace style: kr keeps braces on the header line; allman puts braces on the next line.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the formatter command-line interface."""

    args = build_arg_parser().parse_args(argv)
    try:
        source = read_input(args.input)
        formatted = format_c_code(
            source,
            preserve_line_breaks=args.keep_line_breaks,
            brace_style=args.brace_style,
        )
        write_output(formatted, args.output)
        return 0
    except OSError as exc:
        print(f"c_formatter: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
