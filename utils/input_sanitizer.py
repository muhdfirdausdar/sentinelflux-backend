import re
from typing import Optional


class InputSanitizer:
    """Utility class for sanitizing user inputs for domain searches.

    The primary goal is to prevent SQL injection and other injection attacks by
    restricting the allowed characters and formats for values that will be used
    to build SQL LIKE queries for domain names.

    Rules implemented:
    - Only ASCII letters, digits, hyphen and dot are allowed
    - Labels (parts between dots) must be 1-63 chars and cannot start/end with '-'
    - Consecutive dots (empty labels in the middle) are rejected
    - Leading or trailing dot is allowed to support searches like '.uk' or 'google.'
    - Max overall length is 253 characters
    """

    _LABEL_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
    _ALLOWED_RE = re.compile(r"^[A-Za-z0-9.-]+$")

    @classmethod
    def sanitize_domain_search(cls, term: Optional[str]) -> str:
        """Validate and sanitize a domain search term.

        Returns the stripped term if valid. Raises ValueError on invalid input.

        Examples of accepted terms:
        - "google"
        - "google.com"
        - "docs.google.com"
        - ".uk" (leading dot to search by TLD)

        Disallowed:
        - SQL metacharacters: quotes, semicolon, comments, percent, underscore, spaces
        - consecutive dots ("a..b")
        - labels that start/end with hyphen or are longer than 63 chars
        """
        if term is None:
            raise ValueError("Search term is required")

        term = term.strip()
        if term == "":
            raise ValueError("Search term is empty")

        if len(term) > 253:
            raise ValueError("Search term too long")

        # Only allow a limited set of characters
        if not cls._ALLOWED_RE.match(term):
            raise ValueError("Search term contains invalid characters")

        # Split into labels; allow leading/trailing empty label for leading/trailing dot
        labels = term.split('.')
        for i, label in enumerate(labels):
            if label == "":
                # empty labels allowed only at the start or end (leading/trailing dot)
                if i != 0 and i != len(labels) - 1:
                    raise ValueError("Invalid domain format: consecutive dots")
                continue

            if len(label) > 63:
                raise ValueError("Domain label too long")

            if not cls._LABEL_RE.match(label):
                raise ValueError(f"Invalid domain label: {label}")

        return term


def is_valid_domain_search(term: Optional[str]) -> bool:
    try:
        InputSanitizer.sanitize_domain_search(term)
        return True
    except Exception:
        return False
