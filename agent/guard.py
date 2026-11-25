"""
Voight-Kampff Guard — Jailbreak & Authority-Spoofing Resistance
================================================================
Screens every incoming message for prompt-injection, jailbreak attempts,
and authority-spoofing patterns before it reaches the planner.
"""

import re

# ── Static keyword patterns ─────────────────────────────────────────
_JAILBREAK_KEYWORDS: list[str] = [
    "ignore the law",
    "ignore the rules",
    "ignore all rules",
    "ignore previous",
    "ignore your instructions",
    "ignore your programming",
    "disregard the rules",
    "disregard the law",
    "disregard your instructions",
    "bypass the rules",
    "bypass rules",
    "bypass all",
    "override the rules",
    "override rules",
    "override all",
    "forget your instructions",
    "forget the rules",
    "forget your rules",
    "new instructions",
    "new rules",
    "developer mode",
    "admin mode",
    "sudo mode",
    "sudo",
    "jailbreak",
    "pretend you are",
    "pretend to be",
    "act as if",
    "act as though",
    "roleplay as",
    "you are now",
    "from now on you",
    "do anything now",
    "dan mode",
    "hypothetically",
    "for educational purposes ignore",
    "as a test ignore",
]

# ── Regex patterns for authority spoofing ────────────────────────────
_AUTHORITY_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bi[' ]?a?m\s+the\s+chief\b", re.IGNORECASE),
    re.compile(r"\bi[' ]?a?m\s+(?:your\s+)?(?:boss|manager|admin|supervisor|director)\b", re.IGNORECASE),
    re.compile(r"\bchief[' ]?s?\s+(?:order|command|direct|override|authoriz)", re.IGNORECASE),
    re.compile(r"\bspecial\s+(?:authority|clearance|permission|override)\b", re.IGNORECASE),
    re.compile(r"\boverride\s+(?:code|clearance|authority|permission)\b", re.IGNORECASE),
    re.compile(r"\bmaster\s+(?:code|key|override|password)\b", re.IGNORECASE),
    re.compile(r"\bemergency\s+override\b", re.IGNORECASE),
    re.compile(r"\bexecutive\s+(?:order|privilege|override)\b", re.IGNORECASE),
    re.compile(r"\bgrant\s+(?:me|yourself)\s+(?:clearance|access|permission)\b", re.IGNORECASE),
    re.compile(r"\bpromote\s+(?:me|operator)\b", re.IGNORECASE),
    re.compile(r"\bchange\s+(?:my|the)\s+clearance\b", re.IGNORECASE),
    re.compile(r"\bset\s+clearance\s+(?:to|level)\b", re.IGNORECASE),
    re.compile(r"\bskip\s+(?:the\s+)?(?:rule|check|approval|verification)\b", re.IGNORECASE),
    re.compile(r"\bno\s+(?:need|require)\s+(?:for\s+)?approval\b", re.IGNORECASE),
]


def check_voight_kampff(message: str) -> tuple[bool, str]:
    """Screen a message for jailbreak / authority-spoofing attempts.

    Args:
        message: The raw user message text.

    Returns:
        (True,  "Clear.")  if the message is safe.
        (False, reason)     if a jailbreak/spoofing attempt is detected.
    """
    lower = message.lower()

    # 1. Check keyword patterns
    for pattern in _JAILBREAK_KEYWORDS:
        if pattern in lower:
            return False, (
                f"VOIGHT-KAMPFF ALERT: Detected jailbreak attempt — "
                f"pattern matched: '{pattern}'. Request DENIED. "
                f"All operations MUST comply with The Foundry's operational "
                f"rules. No overrides are permitted regardless of claimed authority."
            )

    # 2. Check regex authority-spoofing patterns
    for regex in _AUTHORITY_PATTERNS:
        match = regex.search(message)
        if match:
            return False, (
                f"VOIGHT-KAMPFF ALERT: Detected authority spoofing — "
                f"matched: '{match.group()}'. Request DENIED. "
                f"Rule [M001]: No operator may override or bypass any "
                f"operational rule. Claims of special authority via chat "
                f"are always rejected."
            )

    return True, "Clear."
