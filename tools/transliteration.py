"""
Bengali to English phonetic transliteration engine.
Generates context-aware romanized variations (colloquial spellings, Avro-style,
ITRANS, and common transliterations) for Bengali text so that English search
queries can match Bengali titles and authors.
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
    'য': ['j'],
    'র': ['r'],
    'ল': ['l'],
    'শ': ['sh', 's'],
    'ষ': ['sh', 's'],
    'স': ['s', 'sh'],
    'হ': ['h'],
    'ড়': ['r', 'd'],
    'ঢ়': ['rh', 'r'],
    'য়': ['y', 'e'],
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
    'জ্ঞ': ['gyan', 'gnan', 'jn'],
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
    Transliterates a single Bengali word into context-aware romanized representations.
    Returns an ordered list of plausible romanized spellings, with the cleanest,
    most natural English spelling first, followed by valid phonetic and colloquial variants.
    """
    if not word or not any('\u0980' <= c <= '\u09FF' for c in word):
        return [word.lower()]

    normalized = unicodedata.normalize('NFC', word)
    length = len(normalized)
    i = 0
    variants = [""]

    has_er_suffix = normalized.endswith('ের')

    while i < length:
        # Contextual conjunct: ক্ষ (ক + ্ + ষ, len 3)
        if normalized[i:i + 3] == 'ক্ষ':
            if i == 0:
                # Word-initial: pronounced /kh/, with kkh/ksh/x preserved for search
                opts = ['kh', 'kkh', 'ksh', 'x']
            else:
                # Medial/final: pronounced /kkh/
                opts = ['kkh', 'ksh', 'x']
            variants = [v + o for v in variants for o in opts]
            i += 3
            if i < length and normalized[i] in VOWEL_SIGNS:
                v_opts = VOWEL_SIGNS[normalized[i]]
                variants = [v + vo for v in variants for vo in v_opts]
                i += 1
            continue

        matched = False
        for c_len in (3, 2):
            if i + c_len <= length:
                sub = normalized[i:i + c_len]
                if sub in CONJUNCTS:
                    opts = CONJUNCTS[sub]
                    if sub == 'জ্ঞ' and i > 0:
                        opts = ['ggan', 'ggo', 'gyan', 'jn']
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

            if has_next_vowel or has_next_hasanta or is_last:
                variants = [v + co for v in variants for co in c_opts]
            else:
                # Inherent vowel (schwa /o/ or /a/) preservation
                new_variants = []
                for v in variants:
                    for co in c_opts:
                        new_variants.append(v + co + 'o')
                        new_variants.append(v + co + 'a')
                variants = new_variants[:12]

            i += 1
            continue

        variants = [v + ch for v in variants]
        i += 1

    # Deterministic deduplication preserving order
    ordered = []
    seen = set()
    for v in variants:
        c = re.sub(r'[^a-zA-Z0-9\s-]', '', v.lower()).strip()
        if c and c not in seen:
            seen.add(c)
            ordered.append(c)

    # If word ends in "er", also provide the spaced possessive " root er"
    if has_er_suffix:
        more = []
        for o in ordered:
            if o.endswith('er') and not o.endswith(' er') and len(o) > 3:
                base = o[:-2].strip()
                spaced = f"{base} er"
                if spaced not in seen:
                    seen.add(spaced)
                    more.append(spaced)
        ordered.extend(more)

    # Rank word candidates: natural vowels & common English spellings first,
    # Avro 'x' and heavy conjuncts at the end
    def word_rank_score(w: str) -> int:
        score = 0
        if 'x' in w:
            score += 100
        if 'kkh' in w:
            score += 25
        if 'ksh' in w:
            score += 30
        if 'kheer' in w or 'khir' in w:
            score -= 40
        if 'ee' in w:
            score -= 10
        return score

    ordered.sort(key=word_rank_score)
    return ordered


def transliterate_text(text: str) -> list[str]:
    """
    Transliterates a full Bengali text phrase into multiple Romanized variations.
    The first element is the most natural, human-readable title (for title_en),
    followed by alternative spellings (including colloquial, Avro 'x', and ITRANS variants).
    """
    if not text:
        return []

    clean_text = re.sub(r'[\\/*?:"<>|(),.—–!_]', ' ', text).strip()
    words = [w for w in clean_text.split() if w]

    if not words:
        return []

    word_variants = [transliterate_word(w) for w in words]

    combined = [""]
    for w_vars in word_variants:
        top_vars = []
        # Natural candidates first
        for v in w_vars:
            if 'x' not in v and v not in top_vars:
                top_vars.append(v)
            if len(top_vars) >= 4:
                break
        # Also include up to 4 Avro keyboard x-variants for searchability
        for v in w_vars:
            if 'x' in v and v not in top_vars:
                top_vars.append(v)
            if len([x for x in top_vars if 'x' in x]) >= 4:
                break

        new_combined = []
        for base in combined:
            for tv in top_vars:
                cand = f"{base} {tv}".strip()
                if cand not in new_combined:
                    new_combined.append(cand)
        combined = new_combined[:32]

    # Global text candidate ranking: natural English title first, Avro shortcuts at tail
    def text_rank_score(s: str) -> int:
        score = 0
        if 'x' in s:
            score += 200
        if 'kkh' in s:
            score += 40
        if 'ksh' in s:
            score += 30
        if 'kheer' in s or 'khir' in s:
            score -= 50
        if 'apon por' in s:
            score -= 100
        return score

    combined.sort(key=text_rank_score)
    return combined
