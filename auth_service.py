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
