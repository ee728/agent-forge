import re

# Surrogate characters are invalid in UTF-8 strings.
# They can appear when terminal input corrupts multi-byte characters
# (e.g. deleting a Chinese character partially with backspace).
_SURROGATE_RE = re.compile(r"[\uD800-\uDFFF]")


def sanitize(text: str) -> str:
	"""Remove surrogate characters and other invalid code points."""
	return _SURROGATE_RE.sub("", text)
