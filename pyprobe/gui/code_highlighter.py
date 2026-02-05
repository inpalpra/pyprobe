"""
Python syntax highlighter with cyberpunk theme colors.

Color scheme:
- Keywords: Magenta (#ff00ff)
- Built-ins: Cyan (#00ffff)
- Strings: Green (#00ff00)
- Numbers: Yellow (#ffff00)
- Comments: Gray italic (#666666)
- Decorators: Orange (#ff8800)
"""

import re
from typing import List, Tuple
from PyQt6.QtGui import (
    QSyntaxHighlighter, QTextDocument, QTextCharFormat, QColor, QFont
)


class PythonHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Python code with cyberpunk theme.

    Applies color highlighting to:
    - Python keywords
    - Built-in functions and constants
    - String literals (single, double, triple-quoted)
    - Numeric literals
    - Comments
    - Decorators
    - Function/class definitions
    """

    # Python keywords
    KEYWORDS = [
        'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
        'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
        'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
        'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try',
        'while', 'with', 'yield'
    ]

    # Python built-in functions
    BUILTINS = [
        'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'breakpoint', 'bytearray',
        'bytes', 'callable', 'chr', 'classmethod', 'compile', 'complex',
        'delattr', 'dict', 'dir', 'divmod', 'enumerate', 'eval', 'exec',
        'filter', 'float', 'format', 'frozenset', 'getattr', 'globals',
        'hasattr', 'hash', 'help', 'hex', 'id', 'input', 'int', 'isinstance',
        'issubclass', 'iter', 'len', 'list', 'locals', 'map', 'max',
        'memoryview', 'min', 'next', 'object', 'oct', 'open', 'ord', 'pow',
        'print', 'property', 'range', 'repr', 'reversed', 'round', 'set',
        'setattr', 'slice', 'sorted', 'staticmethod', 'str', 'sum', 'super',
        'tuple', 'type', 'vars', 'zip', '__import__'
    ]

    def __init__(self, document: QTextDocument):
        super().__init__(document)

        # Create formats for different token types
        self._formats = self._create_formats()

        # Build highlighting rules
        self._rules: List[Tuple[re.Pattern, QTextCharFormat]] = []
        self._build_rules()

        # Multi-line string state
        self._triple_single = re.compile(r"'''")
        self._triple_double = re.compile(r'"""')

    def _create_formats(self) -> dict:
        """Create text formats for each token type."""
        formats = {}

        # Keywords - Magenta
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#ff00ff"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        formats['keyword'] = keyword_format

        # Built-ins - Cyan
        builtin_format = QTextCharFormat()
        builtin_format.setForeground(QColor("#00ffff"))
        formats['builtin'] = builtin_format

        # Strings - Green
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#00ff00"))
        formats['string'] = string_format

        # Numbers - Yellow
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#ffff00"))
        formats['number'] = number_format

        # Comments - Gray italic
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#666666"))
        comment_format.setFontItalic(True)
        formats['comment'] = comment_format

        # Decorators - Orange
        decorator_format = QTextCharFormat()
        decorator_format.setForeground(QColor("#ff8800"))
        formats['decorator'] = decorator_format

        # Function/class names - White (default, but slightly brighter)
        definition_format = QTextCharFormat()
        definition_format.setForeground(QColor("#ffffff"))
        definition_format.setFontWeight(QFont.Weight.Bold)
        formats['definition'] = definition_format

        # Self/cls - Cyan (dimmer)
        self_format = QTextCharFormat()
        self_format.setForeground(QColor("#00cccc"))
        self_format.setFontItalic(True)
        formats['self'] = self_format

        return formats

    def _build_rules(self) -> None:
        """Build the list of highlighting rules."""
        # Keywords
        keyword_pattern = r'\b(' + '|'.join(self.KEYWORDS) + r')\b'
        self._rules.append((
            re.compile(keyword_pattern),
            self._formats['keyword']
        ))

        # Built-ins
        builtin_pattern = r'\b(' + '|'.join(self.BUILTINS) + r')\b'
        self._rules.append((
            re.compile(builtin_pattern),
            self._formats['builtin']
        ))

        # self and cls
        self._rules.append((
            re.compile(r'\b(self|cls)\b'),
            self._formats['self']
        ))

        # Decorators
        self._rules.append((
            re.compile(r'@\w+'),
            self._formats['decorator']
        ))

        # Function and class definitions
        self._rules.append((
            re.compile(r'\bdef\s+(\w+)'),
            self._formats['definition']
        ))
        self._rules.append((
            re.compile(r'\bclass\s+(\w+)'),
            self._formats['definition']
        ))

        # Numbers (integers, floats, hex, binary, octal, complex)
        self._rules.append((
            re.compile(r'\b(0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+|'
                       r'\d+\.?\d*([eE][+-]?\d+)?j?|\.\d+([eE][+-]?\d+)?j?)\b'),
            self._formats['number']
        ))

        # Single-quoted strings (not triple)
        self._rules.append((
            re.compile(r"(?<!')('(?:[^'\\]|\\.)*')(?!')"),
            self._formats['string']
        ))

        # Double-quoted strings (not triple)
        self._rules.append((
            re.compile(r'(?<!")("(?:[^"\\]|\\.)*")(?!")'),
            self._formats['string']
        ))

        # Comments (must come last to override strings in comments)
        self._rules.append((
            re.compile(r'#[^\n]*'),
            self._formats['comment']
        ))

    def highlightBlock(self, text: str) -> None:
        """Apply syntax highlighting to a block of text.

        Args:
            text: The text content of the block
        """
        # Apply single-line rules
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                # Check if pattern has a group (for def/class names)
                if pattern.groups:
                    # Highlight the captured group
                    start = match.start(1)
                    length = match.end(1) - start
                else:
                    start = match.start()
                    length = match.end() - start

                self.setFormat(start, length, fmt)

        # Handle multi-line strings
        self._handle_multiline_strings(text)

    def _handle_multiline_strings(self, text: str) -> None:
        """Handle triple-quoted multi-line strings.

        Args:
            text: The text content of the current block
        """
        # States: 0 = normal, 1 = in triple-single, 2 = in triple-double
        self.setCurrentBlockState(0)

        # Check previous block state
        prev_state = self.previousBlockState()
        start_index = 0

        # If we're continuing a multi-line string
        if prev_state == 1:
            # Look for closing triple-single
            match = self._triple_single.search(text)
            if match:
                end = match.end()
                self.setFormat(0, end, self._formats['string'])
                start_index = end
            else:
                # Entire block is in the string
                self.setFormat(0, len(text), self._formats['string'])
                self.setCurrentBlockState(1)
                return

        elif prev_state == 2:
            # Look for closing triple-double
            match = self._triple_double.search(text)
            if match:
                end = match.end()
                self.setFormat(0, end, self._formats['string'])
                start_index = end
            else:
                # Entire block is in the string
                self.setFormat(0, len(text), self._formats['string'])
                self.setCurrentBlockState(2)
                return

        # Look for new triple-quoted strings starting in this block
        while start_index < len(text):
            # Find the next triple quote
            single_match = self._triple_single.search(text, start_index)
            double_match = self._triple_double.search(text, start_index)

            # Determine which comes first
            if single_match and double_match:
                if single_match.start() < double_match.start():
                    match = single_match
                    state = 1
                    closer = self._triple_single
                else:
                    match = double_match
                    state = 2
                    closer = self._triple_double
            elif single_match:
                match = single_match
                state = 1
                closer = self._triple_single
            elif double_match:
                match = double_match
                state = 2
                closer = self._triple_double
            else:
                break

            # Look for the closing quotes
            close_match = closer.search(text, match.end())
            if close_match:
                # Found closing on same line
                length = close_match.end() - match.start()
                self.setFormat(match.start(), length, self._formats['string'])
                start_index = close_match.end()
            else:
                # String continues to next line
                self.setFormat(match.start(), len(text) - match.start(),
                               self._formats['string'])
                self.setCurrentBlockState(state)
                return
