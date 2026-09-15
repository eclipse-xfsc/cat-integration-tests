"""
Password-policy-conforming random password generation for ephemeral RBAC
test-user provisioning (see keycloak_admin.KeycloakAdmin).

Keycloak's realm-level passwordPolicy attribute is a string of "and"-joined
directives, e.g. "length(8) and specialChars(1) and upperCase(1) and
lowerCase(1) and digits(1)" (this is the shipped dev realm's policy, see
keycloak/realms/dev/fc-realm.json in the federated-catalogue repository --
this module never reads that file; KeycloakAdmin fetches the same string
from the LIVE realm via the Admin API, so cat-integration-tests never
depends on a path inside a sibling repo).

Parsing the live policy (rather than hard-coding a fixed password shape that
happens to satisfy today's realm) is deliberate: a test-side password shape
that only happens to match the realm drifts out of sync the moment the
realm's policy is tightened, and the resulting failure surfaces as an opaque
Keycloak 400 during user provisioning rather than as a test-preparation
problem.
"""
from typing import Optional

import re
import secrets
from dataclasses import dataclass

UPPER_CASE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER_CASE_CHARS = "abcdefghijklmnopqrstuvwxyz"
DIGIT_CHARS = "0123456789"
SPECIAL_CHARS = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"

DIRECTIVE_SEPARATOR = " and "
# The argument is captured as-is (not restricted to digits): numeric directives
# (length/maxLength/specialChars/upperCase/lowerCase/digits) are int-parsed
# below, but an ignored directive's argument need not be numeric at all --
# e.g. Keycloak serializes hashAlgorithm(pbkdf2-sha512).
DIRECTIVE_PATTERN = re.compile(r"^(?P<name>[A-Za-z]+)(?:\((?P<value>[^)]*)\))?$")
DEFAULT_DIRECTIVE_VALUE = 1

DIRECTIVE_LENGTH = "length"
DIRECTIVE_MAX_LENGTH = "maxLength"
DIRECTIVE_SPECIAL_CHARS = "specialChars"
DIRECTIVE_UPPER_CASE = "upperCase"
DIRECTIVE_LOWER_CASE = "lowerCase"
DIRECTIVE_DIGITS = "digits"

# Directives whose argument is an integer count, mapped to the
# PasswordPolicyRequirements field it sets. Every other recognised directive
# (IGNORED_DIRECTIVES) may carry a non-integer argument -- e.g. Keycloak
# serializes hashAlgorithm(pbkdf2-sha512) -- so only these six are ever
# int-parsed.
NUMERIC_DIRECTIVE_FIELDS = {
    DIRECTIVE_LENGTH: "min_length",
    DIRECTIVE_MAX_LENGTH: "max_length",
    DIRECTIVE_SPECIAL_CHARS: "min_special_chars",
    DIRECTIVE_UPPER_CASE: "min_upper_case",
    DIRECTIVE_LOWER_CASE: "min_lower_case",
    DIRECTIVE_DIGITS: "min_digits",
}

# Directives a freshly generated random password satisfies by construction
# (notUsername/notEmail/notContainsUsername: this password is never derived
# from the username or email; passwordHistory: a brand-new user has no
# history) or that describe storage rather than the password's shape
# (hashIterations/hashAlgorithm/forceExpiredPasswordChange). Named
# explicitly so an unrecognised directive fails loudly instead of being
# silently ignored -- see _parse_password_policy.
IGNORED_DIRECTIVES = frozenset({
    "notUsername",
    "notEmail",
    "notContainsUsername",
    "passwordHistory",
    "hashIterations",
    "hashAlgorithm",
    "forceExpiredPasswordChange",
})

# Floors applied to every parsed policy, not just an empty one. A realm may
# define no password policy at all, or one made up entirely of directives
# that say nothing about the password's shape (e.g. "notUsername", or
# "maxLength(20)" on its own) -- without floors those parse cleanly to "no
# requirements" and would yield a zero-length password, which Keycloak then
# rejects with the same opaque 400 this module exists to prevent. Exceeding
# a realm's stated minimums is always safe: no Keycloak policy directive
# forbids length or a character class, it can only require them. Capped by
# maxLength where the realm sets one (see generate_password_for_policy).
FALLBACK_MIN_LENGTH = 16
FALLBACK_MIN_SPECIAL_CHARS = 1
FALLBACK_MIN_UPPER_CASE = 1
FALLBACK_MIN_LOWER_CASE = 1
FALLBACK_MIN_DIGITS = 1


@dataclass
class PasswordPolicyRequirements:
    """Parsed character-class requirements a generated password must satisfy."""

    min_length: int = 0
    max_length: Optional[int] = None
    min_special_chars: int = 0
    min_upper_case: int = 0
    min_lower_case: int = 0
    min_digits: int = 0

    def required_char_count(self) -> int:
        """Sum of the mandatory-per-class minimums (excludes min_length,
        which may exceed this sum and is satisfied by filler characters)."""
        return self.min_special_chars + self.min_upper_case + self.min_lower_case + self.min_digits


def _parse_password_policy(policy: str) -> PasswordPolicyRequirements:
    """Parse a Keycloak passwordPolicy string ("name(arg) and name(arg) and
    name", arg defaulting to 1 when the parentheses are omitted) into the
    character-class requirements a generated password must satisfy.

    Fails loudly (AssertionError naming the directive) on any directive this
    module does not recognise: a future tightening of the realm policy must
    produce an immediately legible failure here, not an obscure downstream
    Keycloak 400.
    """
    stripped = policy.strip() if policy else ""
    requirements = PasswordPolicyRequirements()
    for raw_token in stripped.split(DIRECTIVE_SEPARATOR):
        token = raw_token.strip()
        if not token:
            continue
        match = DIRECTIVE_PATTERN.match(token)
        assert match, f"Could not parse password policy directive '{token}' in policy '{policy}'"
        name = match.group("name")
        raw_value = match.group("value")

        field_name = NUMERIC_DIRECTIVE_FIELDS.get(name)
        if field_name is None:
            if name in IGNORED_DIRECTIVES:
                continue
            raise AssertionError(
                f"password policy directive '{name}' is not supported by RBAC test-user "
                f"provisioning (full policy: '{policy}')"
            )

        if raw_value is None:
            value = DEFAULT_DIRECTIVE_VALUE
        else:
            assert raw_value.lstrip("-").isdigit(), (
                f"password policy directive '{name}({raw_value})' has a non-integer argument "
                f"in policy '{policy}'"
            )
            value = int(raw_value)
        setattr(requirements, field_name, value)

    # Character-class floors are applied here; the length floor is applied in
    # generate_password_for_policy, which is where maxLength can cap it. The
    # realm's own min/max are checked against each other first, on the
    # un-floored values, so a genuinely contradictory realm policy is reported
    # as such rather than as an artefact of our floors.
    assert (
        requirements.max_length is None
        or requirements.min_length <= requirements.max_length
    ), (
        f"password policy '{policy}' is contradictory: length({requirements.min_length}) "
        f"exceeds maxLength({requirements.max_length})"
    )
    requirements.min_special_chars = max(requirements.min_special_chars, FALLBACK_MIN_SPECIAL_CHARS)
    requirements.min_upper_case = max(requirements.min_upper_case, FALLBACK_MIN_UPPER_CASE)
    requirements.min_lower_case = max(requirements.min_lower_case, FALLBACK_MIN_LOWER_CASE)
    requirements.min_digits = max(requirements.min_digits, FALLBACK_MIN_DIGITS)
    return requirements


def generate_password_for_policy(policy: str) -> str:
    """Generate a random password that satisfies every character-class
    requirement in the given Keycloak passwordPolicy string.

    Uses `secrets` throughout, never `random`/`uuid`: one mandatory
    character per required class is drawn with `secrets.choice`, the rest of
    the target length is filled from the combined alphabet the same way, and
    the full sequence is shuffled with `secrets.SystemRandom().shuffle` so a
    character's position never reveals which class filled it. Every call is
    independent: no shared password across provisioned users, and no
    fixed/predictable component (e.g. a constant suffix bolted on to satisfy
    a character class) layered onto a random stem.
    """
    requirements = _parse_password_policy(policy)
    # FALLBACK_MIN_LENGTH is a floor, not a default: a policy that names no
    # length at all (or none beyond maxLength) must still produce a usable
    # password rather than an empty string.
    length = max(requirements.min_length, requirements.required_char_count(), FALLBACK_MIN_LENGTH)
    if requirements.max_length is not None:
        assert requirements.max_length >= requirements.required_char_count(), (
            f"password policy '{policy}' is unsatisfiable: its character-class minimums need "
            f"{requirements.required_char_count()} characters but maxLength allows only "
            f"{requirements.max_length}"
        )
        length = min(length, requirements.max_length)

    mandatory_chars = (
        [secrets.choice(SPECIAL_CHARS) for _ in range(requirements.min_special_chars)]
        + [secrets.choice(UPPER_CASE_CHARS) for _ in range(requirements.min_upper_case)]
        + [secrets.choice(LOWER_CASE_CHARS) for _ in range(requirements.min_lower_case)]
        + [secrets.choice(DIGIT_CHARS) for _ in range(requirements.min_digits)]
    )
    alphabet = SPECIAL_CHARS + UPPER_CASE_CHARS + LOWER_CASE_CHARS + DIGIT_CHARS
    filler_chars = [secrets.choice(alphabet) for _ in range(length - len(mandatory_chars))]

    password_chars = mandatory_chars + filler_chars
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)
