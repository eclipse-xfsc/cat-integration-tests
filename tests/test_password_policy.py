# pylint: disable=missing-module-docstring
import re

import pytest

from eu.xfsc.bdd.cat.components.password_policy import (
    DIGIT_CHARS, FALLBACK_MIN_LENGTH, LOWER_CASE_CHARS, SPECIAL_CHARS,
    UPPER_CASE_CHARS, PasswordPolicyRequirements,
    generate_password_for_policy)

DEV_REALM_POLICY = "length(8) and specialChars(1) and upperCase(1) and lowerCase(1) and digits(1)"
STRICT_POLICY = "length(20) and specialChars(3) and upperCase(2) and lowerCase(2) and digits(2)"


def _count(password: str, alphabet: str) -> int:
    return sum(1 for char in password if char in alphabet)


def _char_class(char: str) -> str:
    for name, alphabet in (
        ("special", SPECIAL_CHARS),
        ("upper", UPPER_CASE_CHARS),
        ("lower", LOWER_CASE_CHARS),
        ("digit", DIGIT_CHARS),
    ):
        if char in alphabet:
            return name
    raise AssertionError(f"character '{char}' is not in any known password alphabet")


def _assert_satisfies(password: str, requirements: PasswordPolicyRequirements) -> None:
    assert len(password) >= requirements.min_length
    assert _count(password, SPECIAL_CHARS) >= requirements.min_special_chars
    assert _count(password, UPPER_CASE_CHARS) >= requirements.min_upper_case
    assert _count(password, LOWER_CASE_CHARS) >= requirements.min_lower_case
    assert _count(password, DIGIT_CHARS) >= requirements.min_digits


def test_generated_password_satisfies_shipped_dev_policy():
    """
    Given the shipped dev realm's passwordPolicy string
    When generate_password_for_policy is called with it
    Then the result satisfies length(8)/specialChars(1)/upperCase(1)/lowerCase(1)/digits(1)
    """
    password = generate_password_for_policy(DEV_REALM_POLICY)
    _assert_satisfies(password, PasswordPolicyRequirements(
        min_length=8, min_special_chars=1, min_upper_case=1, min_lower_case=1, min_digits=1,
    ))


def test_generated_password_satisfies_a_stricter_policy():
    """
    Given a stricter policy than the shipped dev realm's
    When generate_password_for_policy is called with it
    Then the result satisfies length(20)/specialChars(3)/upperCase(2)/lowerCase(2)/digits(2)
    """
    password = generate_password_for_policy(STRICT_POLICY)
    _assert_satisfies(password, PasswordPolicyRequirements(
        min_length=20, min_special_chars=3, min_upper_case=2, min_lower_case=2, min_digits=2,
    ))


def test_successive_calls_produce_different_passwords():
    """
    Given the shipped dev realm's passwordPolicy string
    When generate_password_for_policy is called twice
    Then the two generated passwords differ (each provisioned user gets its own)
    """
    first = generate_password_for_policy(DEV_REALM_POLICY)
    second = generate_password_for_policy(DEV_REALM_POLICY)
    assert first != second


def test_generated_password_shuffles_mandatory_and_filler_characters():
    """
    Given the shipped dev realm's passwordPolicy string (exactly one
    mandatory character per class, so an unshuffled mandatory-then-filler
    ordering would put a special char at position 0 on every call)
    When generate_password_for_policy is called repeatedly
    Then the character class at position 0 is not always the same -- pinning
    secrets.SystemRandom().shuffle(password_chars), whose removal the
    generator's own docstring calls out ("a character's position never
    reveals which class filled it")
    """
    first_char_classes = {
        _char_class(generate_password_for_policy(DEV_REALM_POLICY)[0])
        for _ in range(30)
    }
    assert len(first_char_classes) > 1


def test_unsupported_directive_raises_naming_it():
    """
    Given a policy string containing a directive this module does not support
    When generate_password_for_policy is called with it
    Then it raises an AssertionError naming that directive
    """
    with pytest.raises(AssertionError, match=re.escape("'regexPattern'")):
        generate_password_for_policy("length(8) and regexPattern(1)")


def test_empty_policy_still_produces_a_strong_password():
    """
    Given an empty passwordPolicy string (realm defines no policy at all)
    When generate_password_for_policy is called with it
    Then it still produces a password with every character class represented
    """
    password = generate_password_for_policy("")
    _assert_satisfies(password, PasswordPolicyRequirements(
        min_length=FALLBACK_MIN_LENGTH, min_special_chars=1, min_upper_case=1, min_lower_case=1, min_digits=1,
    ))


def test_ignored_directives_do_not_affect_generation():
    """
    Given a policy mixing satisfy-directives with by-construction/irrelevant ones
    When generate_password_for_policy is called with it
    Then the ignored directives are accepted and the satisfy-directives still hold
    """
    policy = DEV_REALM_POLICY + " and notUsername and passwordHistory(3) and hashIterations(27500)"
    password = generate_password_for_policy(policy)
    _assert_satisfies(password, PasswordPolicyRequirements(
        min_length=8, min_special_chars=1, min_upper_case=1, min_lower_case=1, min_digits=1,
    ))


def test_ignored_directive_with_non_numeric_argument_does_not_raise():
    """
    Given a policy where an ignored directive carries a non-integer argument
    (Keycloak serializes e.g. hashAlgorithm(pbkdf2-sha512), notUsername(undefined))
    When generate_password_for_policy is called with it
    Then it does not raise, and the satisfy-directives still hold
    """
    policy = DEV_REALM_POLICY + " and hashAlgorithm(pbkdf2-sha512) and notUsername(undefined)"
    password = generate_password_for_policy(policy)
    _assert_satisfies(password, PasswordPolicyRequirements(
        min_length=8, min_special_chars=1, min_upper_case=1, min_lower_case=1, min_digits=1,
    ))


def test_numeric_directive_with_non_integer_argument_raises():
    """
    Given a policy where a numeric (satisfy) directive carries a non-integer argument
    When generate_password_for_policy is called with it
    Then it raises an AssertionError naming the offending directive
    """
    with pytest.raises(AssertionError, match=re.escape("length(eight)")):
        generate_password_for_policy("length(eight) and specialChars(1)")


@pytest.mark.parametrize("policy", [
    "notUsername",
    "maxLength(20)",
    "hashIterations(27500)",
    "notUsername and passwordHistory(3)",
])
def test_policy_without_a_length_directive_still_yields_a_usable_password(policy):
    """
    Given a realm policy that parses cleanly but names no length or character
    class at all -- a loosened realm, the mirror image of a tightened one
    When generate_password_for_policy is called with it
    Then the result is a usable strong password, never an empty string

    An empty password is rejected by Keycloak with the same opaque HTTP 400
    that a policy-violating password produces, so the failure would surface
    during user provisioning with no indication of its real cause.
    """
    password = generate_password_for_policy(policy)
    _assert_satisfies(password, PasswordPolicyRequirements(
        min_length=1, min_special_chars=1, min_upper_case=1, min_lower_case=1, min_digits=1,
    ))


def test_max_length_caps_the_generated_password():
    """
    Given a policy whose maxLength is below the generator's own length floor
    When generate_password_for_policy is called with it
    Then the password is capped at maxLength and still carries every required class
    """
    password = generate_password_for_policy(
        "maxLength(6) and specialChars(1) and upperCase(1) and lowerCase(1) and digits(1)"
    )
    assert len(password) == 6
    _assert_satisfies(password, PasswordPolicyRequirements(
        min_special_chars=1, min_upper_case=1, min_lower_case=1, min_digits=1,
    ))


def test_max_length_below_the_character_class_minimums_raises():
    """
    Given a policy whose maxLength cannot fit its own character-class minimums
    When generate_password_for_policy is called with it
    Then it raises an AssertionError calling the policy unsatisfiable
    """
    with pytest.raises(AssertionError, match="unsatisfiable"):
        generate_password_for_policy("maxLength(2) and specialChars(1) and upperCase(1)")


def test_length_exceeding_max_length_is_reported_as_contradictory():
    """
    Given a realm policy whose own length() exceeds its own maxLength()
    When generate_password_for_policy is called with it
    Then it raises an AssertionError naming the contradiction, so the realm's
    policy is blamed rather than the generator's internal floors
    """
    with pytest.raises(AssertionError, match="contradictory"):
        generate_password_for_policy("length(30) and maxLength(10)")
