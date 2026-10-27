"""Formatting of plain numbers: significant digits and power-of-ten notation.

Both classes only touch *plain real numbers* (``int``, ``float``, ``Decimal``,
``Fraction``, and subclasses such as numpy scalars).  Symbolic objects, strings,
``bool`` and complex numbers fall through to ``str`` and are left alone.

:class:`SignificantDigits` implements ``mpt.configure(precision=n)``;
:class:`PowerOfTen` implements ``mpt.configure(number_format="power")``.  Both
are pure text transformations: they never change the value of the expression.
"""

import decimal
import io
import re
import tokenize
from fractions import Fraction


def is_real_number(value):
    """Whether `value` is a plain real number (``bool`` excluded)."""
    return not isinstance(value, bool) and isinstance(
        value, (int, float, decimal.Decimal, Fraction)
    )


class SignificantDigits:
    """Round a plain number to ``n`` significant digits for display.

    Trailing zeros are dropped (``23.00134`` -> ``"23"``, ``2.50`` -> ``"2.5"``);
    there is no padding.  A value that is not a plain number returns ``None``,
    so the caller can fall back to ``str``.
    """

    @staticmethod
    def format(value, digits):
        """`value` with `digits` significant digits, or ``None`` if not a number."""
        if isinstance(value, bool):
            return None
        if not isinstance(value, (int, float, complex, decimal.Decimal, Fraction)):
            return None
        if isinstance(value, complex):
            real = SignificantDigits._real(value.real, digits)
            imag = SignificantDigits._real(abs(value.imag), digits)
            if value.imag == 0:
                return real
            return f"{real}{'-' if value.imag < 0 else '+'}{imag}j"
        return SignificantDigits._real(value, digits)

    @staticmethod
    def _real(value, digits):
        """Format a real number with `digits` significant digits."""
        with decimal.localcontext() as ctx:
            ctx.prec = max(28, digits + 10)
            number = SignificantDigits._to_decimal(value)
            if number == 0:
                return "0"
            exponent = number.adjusted()
            quantum = decimal.Decimal(1).scaleb(exponent - digits + 1)
            try:
                rounded = number.quantize(quantum, rounding=decimal.ROUND_HALF_EVEN)
            except decimal.InvalidOperation:
                return str(value)
            text = format(rounded, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text

    @staticmethod
    def _to_decimal(value):
        """Lossless-ish conversion of a plain number to `decimal.Decimal`."""
        if isinstance(value, decimal.Decimal):
            return value
        if isinstance(value, Fraction):
            return decimal.Decimal(value.numerator) / decimal.Decimal(value.denominator)
        if isinstance(value, int):
            return decimal.Decimal(value)
        # float subclass (e.g. numpy.float64): `float` normalizes repr quirks.
        return decimal.Decimal(repr(float(value)))


class PowerOfTen:
    """Show numbers as a mantissa times a power of ten (``1.6*10**-19``).

    Two kinds of ``NUMBER`` token are rewritten:

    * anything already in scientific notation -- ``1.23e-09`` ->
      ``1.23*10**-9`` (the exponent loses a sign ``+`` and leading zeros);
    * a plain decimal far from ``1`` -- below ``10**-4`` or at/above ``10**16``
      -- is normalized: ``0.0001106`` -> ``1.106*10**-4``.

    Only ``NUMBER`` tokens are touched, so names (``ro_Si3N4``) and string
    contents are left alone.
    """

    #: A plain decimal number, as ``tokenize`` reports a ``NUMBER`` token.
    _PLAIN_NUMBER = re.compile(r"(?:\d+(?:\.\d+)?|\.\d+)\Z")

    #: Scientific notation, as ``tokenize`` reports a ``NUMBER`` token.
    _SCIENTIFIC_NUMBER = re.compile(
        r"(?P<mantissa>\d+(?:\.\d+)?|\.\d+)[eE](?P<exponent>[+-]?\d+)\Z"
    )

    #: A displayed decimal below this power of ten uses the ``*10**`` form.
    SMALLEST_PLAIN_EXPONENT = -4

    #: A displayed decimal at or above this power of ten uses the ``*10**`` form.
    LARGEST_PLAIN_EXPONENT = 16

    #: Tokens that carry no syntax, skipped when looking for neighbours.
    _IGNORED_TOKENS = frozenset({
        tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT,
        tokenize.ENCODING, tokenize.ENDMARKER, tokenize.COMMENT,
    })

    #: A power-of-ten product produced here: a mantissa and ``*10**n``.
    _POWER_PRODUCT = re.compile(r"\*\s*10\s*\*\*\s*[+-]?\d+\Z")

    #: A ``str.format`` placeholder, e.g. ``{}`` (or a numbered ``{0}``).
    _PLACEHOLDER = re.compile(r"\{(\d*)\}")

    @classmethod
    def rewrite(cls, text):
        """Rewrite the numbers in `text` as powers of ten.

        The replacement is a product, so where it would bind differently from
        the literal it is parenthesized: ``x / 1.6e-19`` becomes
        ``x / (1.6*10**-19)`` (otherwise the trailing ``*10**-19`` would move
        out of the denominator), and ``1.6e-19**2`` becomes
        ``(1.6*10**-19)**2``.
        """
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
        except (tokenize.TokenError, IndentationError, SyntaxError):
            return text

        starts = [0]
        for line in text.splitlines(keepends=True):
            starts.append(starts[-1] + len(line))

        def offset(position):
            row, column = position
            return starts[row - 1] + column

        significant = [t for t in tokens if t.type not in cls._IGNORED_TOKENS]
        replacements = []
        for index, token in enumerate(significant):
            if token.type != tokenize.NUMBER:
                continue
            rewritten = cls._number_as_power(token.string)
            if rewritten == token.string:
                continue
            if cls._needs_parentheses(significant, index):
                rewritten = f"({rewritten})"
            replacements.append(
                (offset(token.start), offset(token.end), rewritten)
            )

        # Splice from the end, so earlier offsets stay valid.
        for start, end, rewritten in reversed(replacements):
            text = text[:start] + rewritten + text[end:]
        return text

    @classmethod
    def fill_template(cls, template, values):
        """Fill a ``str.format`` `template` with power-formatted `values`.

        The template's own numeric literals are rewritten first.  Then each
        value is inserted; a value that is itself a power product gets
        parentheses when the placeholder follows a division or a power, for the
        same reason a rewritten literal does.
        """
        template = cls.rewrite(template)
        values = list(values)
        auto_index = 0
        for match in cls._PLACEHOLDER.finditer(template):
            if match.start() and template[match.start() - 1] == "{":
                continue  # an escaped literal brace, e.g. "{{}}"
            if match.group(1):
                index = int(match.group(1))
            else:
                index = auto_index
                auto_index += 1
            if index >= len(values):
                continue
            value = values[index]
            if (
                isinstance(value, str)
                and cls._POWER_PRODUCT.search(value)
                and cls._text_needs_parentheses(template[:match.start()])
            ):
                values[index] = f"({value})"
        return template.format(*values)

    @classmethod
    def _needs_parentheses(cls, tokens, index):
        """Whether the rewritten number `tokens[index]` needs parentheses.

        The power form is a product, so it must be grouped where the literal
        was a single operand: as the denominator of a division (otherwise its
        ``*10**n`` escapes and lands in the numerator) and as a base or an
        exponent of ``**``.
        """
        following = tokens[index + 1] if index + 1 < len(tokens) else None
        if following is not None and following.string == "**":
            return True
        previous = tokens[index - 1] if index > 0 else None
        if previous is None:
            return False
        if previous.string in ("**", "/", "//", "%"):
            return True
        if previous.string in ("+", "-"):
            # The sign belongs to the number; only the operator before it
            # decides (``x / -1e-9`` vs ``a - 1e-9``).
            before = tokens[index - 2] if index > 1 else None
            return before is not None and before.string in ("**", "/", "//", "%")
        return False

    @staticmethod
    def _text_needs_parentheses(before):
        """Whether a value inserted right after `before` needs parentheses."""
        text = before.rstrip()
        if not text:
            return False
        if text.endswith("**") or text[-1] in "/%":
            return True
        if text[-1] in "+-":
            rest = text[:-1].rstrip()
            return bool(rest) and (rest.endswith("**") or rest[-1] in "/%")
        return False

    @classmethod
    def _number_as_power(cls, token):
        """Rewrite one ``NUMBER`` token, or return it unchanged."""
        scientific = cls._SCIENTIFIC_NUMBER.match(token)
        if scientific:
            mantissa = scientific.group("mantissa")
            exponent = int(scientific.group("exponent"))
            return f"{mantissa}*10**{exponent}"
        if not cls._PLAIN_NUMBER.match(token):
            return token
        value = decimal.Decimal(token)
        if value == 0:
            return token
        exponent = value.adjusted()
        if not (
            exponent <= cls.SMALLEST_PLAIN_EXPONENT
            or exponent >= cls.LARGEST_PLAIN_EXPONENT
        ):
            return token
        with decimal.localcontext() as ctx:
            ctx.prec = max(28, len(value.as_tuple().digits) + 1)
            mantissa = value.scaleb(-exponent).normalize()
        return f"{format(mantissa, 'f')}*10**{exponent}"
