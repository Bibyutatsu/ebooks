"""
Bengali to English phonetic transliteration engine.
Generates romanized variations (Avro-style, ITRANS, and colloquial spellings)
for Bengali text so that English search queries can match Bengali titles and authors.
"""

import re
import unicodedata

# Consonant phonetics mapping
CONSONANTS = {
    'ক': ['k'],
    'খ': ['kh'],
    'গ': ['g'],
    'ঘ': ['gh'],
    'ঙ': ['ng'],
    'চ': ['ch'],
    'ছ': ['chh', 'ch'],
    'জ': ['j'],
    'ঝ': ['jh'],
    'ঞ': ['n'],
    'ট': ['t'],
    'ঠ': ['th'],
    'ড': ['d'],
    'ঢ': ['dh'],
    'ণ': ['n'],
    'ত': ['t'],
    'থ': ['th'],
    'দ': ['d'],
    'ধ': ['dh'],
    'ন': ['n'],
    'প': ['p'],
    'ফ': ['ph', 'f'],
    'ব': ['b'],
    'ভ': ['bh', 'v'],
    'ম': ['m'],
    'য': ['j', 'y'],
    'র': ['r'],
    'ল': ['l'],
    'শ': ['sh', 's'],
    'ষ': ['sh', 's'],
    'স': ['s', 'sh'],
    'হ': ['h'],
    'ড়': ['r'],
    'ঢ়': ['rh', 'r'],
    'য়': ['y'],
    'ৎ': ['t'],
    'ং': ['ng'],
    'ঃ': ['h'],
    'ঁ': ['n'],
}

# Vowels (Independent)
VOWELS = {
    'অ': ['o', 'a'],
    'আ': ['a', 'aa'],
    'ই': ['i', 'ee'],
    'ঈ': ['ee', 'i'],
    'উ': ['u', 'oo'],
    'ঊ': ['oo', 'u'],
    'ঋ': ['ri'],
    'এ': ['e'],
    'ঐ': ['oi', 'ai'],
    'ও': ['o'],
    'ঔ': ['ou', 'au'],
}

# Vowel Signs (কার)
VOWEL_SIGNS = {
    'া': ['a'],
    'ি': ['i'],
    'ী': ['ee', 'i'],
    'ু': ['u'],
    'ূ': ['oo', 'u'],
    'ৃ': ['ri'],
    'ে': ['e'],
    'ৈ': ['oi'],
    'ো': ['o'],
    'ৌ': ['ou'],
}

# Common Bengali conjuncts mapping
CONJUNCTS = {
    'ক্ষ': ['kkh', 'ksh', 'x'],
    'জ্ঞ': ['ggo', 'gyan', 'jn'],
    'ঞ্চ': ['nch'],
    'ঞ্ছ': ['nchh'],
    'ঞ্জ': ['nj'],
    'ঙ্ক': ['nk'],
    'ঙ্গ': ['ng'],
    'ণ্ট': ['nt'],
    'ণ্ঠ': ['nth'],
    'ণ্ড': ['nd'],
    'ন্ত': ['nt'],
    'ন্থ': ['nth'],
    'ন্দ': ['nd'],
    'ন্ধ': ['ndh'],
    'ম্প': ['mp'],
    'ম্ব': ['mb'],
    'ম্ভ': ['mbh'],
    'ল্ক': ['lk'],
    'ল্গ': ['lg'],
    'ল্প': ['lp'],
    'ল্ফ': ['lf'],
    'ল্ব': ['lb'],
    'ল্ম': ['lm'],
    'শ্চ': ['shch'],
    'শ্ছ': ['shchh'],
    'ষ্ট': ['sht', 'st'],
    'ষ্ঠ': ['shth'],
    'ষ্ণ': ['shn'],
    'স্প': ['sp'],
    'স্ফ': ['sf'],
    'স্ত': ['st'],
    'স্থ': ['sth'],
    'স্ন': ['sn'],
    'স্ম': ['sm'],
    'ত্র': ['tr'],
    'শ্র': ['shr', 'sr'],
    'প্র': ['pr'],
    'ব্র': ['br'],
    'গ্র': ['gr'],
    'দ্র': ['dr'],
    'ধ্র': ['dhr'],
    'ক্র': ['kr'],
    'ব্দ': ['bd'],
    'দ্ধ': ['ddh'],
}

HASANTA = '্'


def transliterate_word(word: str) -> list[str]:
    """
    Transliterates a single Bengali word into romanized representations.
    Returns a list of plausible romanized spellings.
    """
    if not word or not any('\u0980' <= c <= '\u09FF' for c in word):
        return [word.lower()]

    normalized = unicodedata.normalize('NFC', word)
    
    i = 0
    length = len(normalized)
    variants = [""]

    while i < length:
        matched = False
        for c_len in (3, 2):
            if i + c_len <= length:
                sub = normalized[i:i + c_len]
                if sub in CONJUNCTS:
                    opts = CONJUNCTS[sub]
                    variants = [v + o for v in variants for o in opts]
                    i += c_len
                    if i < length and normalized[i] in VOWEL_SIGNS:
                        v_opts = VOWEL_SIGNS[normalized[i]]
                        variants = [v + vo for v in variants for vo in v_opts]
                        i += 1
                    matched = True
                    break
        if matched:
            continue

        ch = normalized[i]

        if ch == HASANTA:
            i += 1
            continue

        if ch in VOWELS:
            v_opts = VOWELS[ch]
            variants = [v + vo for v in variants for vo in v_opts]
            i += 1
            continue

        if ch in VOWEL_SIGNS:
            vo_opts = VOWEL_SIGNS[ch]
            variants = [v + vo for v in variants for vo in vo_opts]
            i += 1
            continue

        if ch in CONSONANTS:
            c_opts = CONSONANTS[ch]
            has_next_vowel = (i + 1 < length and normalized[i + 1] in VOWEL_SIGNS)
            has_next_hasanta = (i + 1 < length and normalized[i + 1] == HASANTA)
            is_last = (i + 1 == length)

            if has_next_vowel or has_next_hasanta:
                variants = [v + co for v in variants for co in c_opts]
            elif is_last:
                variants = [v + co for v in variants for co in c_opts]
            else:
                new_variants = []
                for v in variants:
                    for co in c_opts:
                        new_variants.append(v + co + 'o')
                        new_variants.append(v + co + 'a')
                        new_variants.append(v + co)
                variants = new_variants[:12]

            i += 1
            continue

        variants = [v + ch for v in variants]
        i += 1

    clean_results = set()
    for v in variants:
        c = re.sub(r'[^a-zA-Z0-9\s-]', '', v.lower()).strip()
        if c:
            clean_results.add(c)
    return list(clean_results)


def transliterate_text(text: str) -> list[str]:
    """
    Transliterates a full Bengali text phrase into multiple Romanized variations.
    """
    if not text:
        return []

    clean_text = re.sub(r'[\\/*?:"<>|(),.—–!_]', ' ', text).strip()
    words = [w for w in clean_text.split() if w]

    if not words:
        return []

    word_variants = [transliterate_word(w) for w in words]

    combined = {""}
    for w_vars in word_variants:
        top_vars = w_vars[:2]
        new_combined = set()
        for base in combined:
            for tv in top_vars:
                new_combined.add(f"{base} {tv}".strip())
        combined = new_combined

    results = list(combined)
    return sorted(results, key=lambda s: len(s))
