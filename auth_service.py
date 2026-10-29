"""
Authentication and Recovery Phrase service for Personal Expense Tracker.
Handles password hashing, 12-word mnemonic backup generation, and account recovery.
"""
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

# 128 memorable, unambiguous dictionary words for backup recovery phrases
RECOVERY_WORDLIST = [
    "acorn", "amber", "anchor", "apple", "apron", "artist", "atom", "autumn",
    "badge", "bamboo", "beacon", "blossom", "breeze", "bridge", "bronze", "cabin",
    "cactus", "canvas", "castle", "cedar", "canyon", "cherry", "clover", "comet",
    "coral", "cosmos", "crater", "crystal", "dawn", "delta", "desert", "dolphin",
    "dragon", "drift", "eagle", "earth", "echo", "ember", "falcon", "feather",
    "forest", "fossil", "galaxy", "garden", "glacier", "golden", "granite", "harbor",
    "haven", "hawk", "hazel", "horizon", "island", "ivory", "jasper", "jungle",
    "kinetic", "knight", "lagoon", "lantern", "laurel", "legend", "lemon", "liberty",
    "lotus", "lunar", "marble", "meadow", "meteor", "mirage", "monarch", "moss",
    "nebula", "nectar", "nexus", "nomad", "nova", "oasis", "ocean", "olive",
    "orbit", "orchid", "pacific", "palace", "path", "pearl", "pebble", "phoenix",
    "pinnacle", "planet", "polar", "prism", "quartz", "quiver", "radiant", "rainbow",
    "ravine", "reef", "ripple", "river", "rover", "ruby", "saffron", "sailor",
    "sapphire", "shadow", "shimmer", "sierra", "silver", "solar", "spark", "spirit",
    "spring", "star", "stream", "summit", "sunset", "surge", "temple", "timber",
    "topaz", "trail", "tulip", "twilight", "umbra", "valley", "velvet", "venture",
    "vessel", "vigor", "violet", "voyage", "walnut", "wave", "whisper", "willow",
    "winter", "zenith", "zephyr"
]

def generate_recovery_phrase(num_words=12):
    """
    Generates a cryptographically random list of memorable backup keywords.
    Returns: list of words and joined space-separated string.
    """
    words = [secrets.choice(RECOVERY_WORDLIST) for _ in range(num_words)]
    return words, " ".join(words)

def normalize_phrase(phrase_str):
    """Normalizes keywords: lowercase, strips punctuation, and standardizes spacing."""
    if not phrase_str:
        return ""
    words = [w.strip().lower() for w in phrase_str.replace(",", " ").replace("-", " ").split()]
    return " ".join(words)

def hash_phrase(phrase_str):
    """Generates a secure hash for a normalized recovery phrase."""
    return generate_password_hash(normalize_phrase(phrase_str))

def verify_phrase(stored_hash, candidate_phrase):
    """Verifies candidate recovery phrase against stored hash."""
    return check_password_hash(stored_hash, normalize_phrase(candidate_phrase))

def hash_password(password):
    return generate_password_hash(password)

def verify_password(stored_hash, candidate_password):
    return check_password_hash(stored_hash, candidate_password)

import base64
import hashlib
import hmac
import struct
import time
import urllib.parse

def generate_totp_secret():
    """Generates a random 160-bit Base32 secret for TOTP (Google Authenticator compatible)."""
    random_bytes = secrets.token_bytes(20)
    return base64.b32encode(random_bytes).decode("utf-8").replace("=", "")

def get_totp_uri(secret, username, issuer="FinanceFlow"):
    """Returns an otpauth:// URI for scanning into authenticator apps."""
    account_label = urllib.parse.quote(f"{issuer}:{username}")
    issuer_param = urllib.parse.quote(issuer)
    return f"otpauth://totp/{account_label}?secret={secret}&issuer={issuer_param}&algorithm=SHA1&digits=6&period=30"

def generate_totp_code(secret, t=None, time_step=30):
    """Generates the 6-digit TOTP code for the given secret at timestamp t (RFC 6238)."""
    if t is None:
        t = time.time()
    counter = int(t // time_step)
    
    # Pad secret if padding was stripped
    padding = '=' * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode((secret + padding).upper())
    
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    
    offset = h[-1] & 0x0F
    binary = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
    code = binary % 1000000
    return f"{code:06d}"

def verify_totp_code(secret, candidate_code, window=1, time_step=30):
    """
    Verifies candidate 6-digit TOTP code against current and neighboring time steps.
    Window=1 checks current interval, previous 30s, and next 30s for clock skew.
    """
    if not secret or not candidate_code:
        return False
    
    candidate = str(candidate_code).strip()
    if len(candidate) != 6 or not candidate.isdigit():
        return False
    
    current_time = time.time()
    for w in range(-window, window + 1):
        t = current_time + (w * time_step)
        if generate_totp_code(secret, t, time_step) == candidate:
            return True
    return False
