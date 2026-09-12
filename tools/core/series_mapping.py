"""
Rules and keywords to automatically detect popular Bengali literary series and characters.
"""
import re

SERIES_RULES = [
    {
        "id": "feluda",
        "name_bn": "ফেলুদা",
        "name_en": "Feluda",
        "keywords_bn": [
            "ফেলুদা", "তোপসে", "জটায়ু", "লালমোহন", "সোনার কেল্লা", "জয়বাবা ফেলুনাথ",
            "বাদশাহী আংটি", "বোম্বাইয়ের বোম্বেটে", "টিনটোরেটোর যীশু", "কৈলাসে কেলেঙ্কারী",
            "গোরস্থানে সাবধান", "রয়েল বেঙ্গল রহস্য", "ছিন্নমস্তার অভিশাপ", "গোলাপি মুক্তা",
            "লন্ডনে ফেলুদা", "ডবল ফেলুদা", "ফেলুদার গোয়েন্দাগিরি"
        ],
        "keywords_en": ["feluda", "topshe", "jatayu", "lalmohan ganguly", "sonar kella", "badsahi angti"],
        "authors": ["সত্যজিৎ রায়", "সত্যজিৎ রায়", "satyajit ray"]
    },
    {
        "id": "byomkesh",
        "name_bn": "ব্যোমকেশ বক্সী",
        "name_en": "Byomkesh Bakshi",
        "keywords_bn": [
            "ব্যোমকেশ", "বোমক্যাশ", "সত্যান্বেষী", "দুর্গরহস্য", "সজারুর কাঁটা",
            "অর্থমনর্থম", "চিত্রচোর", "আদিম রিপু", "বেণীসংহার", "লোহার বিস্কুট", "ব্যোমকেশ ও বরদা"
        ],
        "keywords_en": ["byomkesh", "bomkesh", "satyanweshi", "durgo rahasya"],
        "authors": ["শরদিন্দু বন্দ্যোপাধ্যায়", "শরদিন্দু বন্দ্যোপাধ্যায়", "saradindu", "sharadindu"]
    },
    {
        "id": "shonku",
        "name_bn": "প্রফেসর শঙ্কু",
        "name_en": "Professor Shonku",
        "keywords_bn": [
            "প্রফেসর শঙ্কু", "প্রোফেসর শঙ্কু", "শঙ্কু সমগ্র", "পাঁচ শঙ্কু", "শঙ্কু একাই ১০০",
            "মিরাকিউরল", "একশৃঙ্গ অভিযান", "নকুড়বাবু ও এল ডোরাডো", "মরু রহস্য", "কোচাবাম্বার গুহা"
        ],
        "keywords_en": ["professor shonku", "prof shonku", "shonku", "prof shanku"],
        "authors": ["সত্যজিৎ রায়", "সত্যজিৎ রায়", "satyajit ray"]
    },
    {
        "id": "kakababu",
        "name_bn": "কাকাবাবু",
        "name_en": "Kakababu",
        "keywords_bn": [
            "কাকাবাবু", "রাজা রায়চৌধুরী", "পাহাড়চূড়ায় আতঙ্ক", "সবুজ দ্বীপের রাজা",
            "ভূপাল রহস্য", "মিশর রহস্য", "জঙ্গলের মধ্যে এক হোটেল"
        ],
        "keywords_en": ["kakababu", "mishor rahasya", "sabuj dwiper raja"],
        "authors": ["সুনীল গঙ্গোপাধ্যায়", "সুনীল গঙ্গোপাধ্যায়", "sunil gangopadhyay"]
    },
    {
        "id": "masud_rana",
        "name_bn": "মাসুদ রানা",
        "name_en": "Masud Rana",
        "keywords_bn": ["মাসুদ রানা"],
        "keywords_en": ["masud rana", "major rana"],
        "author_specific_titles_bn": ["ধ্বংস পাহাড়", "ভারতনাট্যম", "স্বর্ণমৃগ"],
        "authors": ["কাজী আনোয়ার হোসেন", "কাজী আনোয়ার", "qazi anwar", "anwar hussain"]
    },
    {
        "id": "tin_goyenda",
        "name_bn": "তিন গোয়েন্দা",
        "name_en": "Tin Goyenda",
        "keywords_bn": ["তিন গোয়েন্দা", "তিন গোয়েন্দা", "কিশোর পাশা", "মুসা আমান", "রবিন মিলফোর্ড"],
        "keywords_en": ["tin goyenda", "teen goyenda", "three detectives"],
        "authors": ["রকিব হাসান", "রাকিব হাসান", "rakib hasan", "সেবা প্রকাশনী"]
    },
    {
        "id": "himu",
        "name_bn": "হিমু",
        "name_en": "Himu",
        "keywords_bn": [
            "হিমু", "হলুদ হিমু", "ময়ূরাক্ষী", "দরজার ওপাশে", "হিমুর হাতে কয়েকটি নীলপদ্ম",
            "হিমুর দ্বিতীয় প্রহর", "হিমুর দ্বিতীয় প্রহর", "আঙুল কাটা জগলু", "আজ হিমুর বিয়ে",
            "আজ হিমুর বিয়ে", "হিমুর নীল জোছনা", "হিমুর বাবার কথামালা", "হিমুর মধ্যদুপুর",
            "হিমুর রূপালী রাত্রি", "হিমুর আছে জল", "হিমু রিমান্ডে", "হিমু মামা", "হিমু সমগ্র"
        ],
        "keywords_en": ["himu", "holud himu", "mayurakkhi", "himur"],
        "authors": ["হুমায়ূন আহমেদ", "হুমায়ূন আহমেদ", "humayun ahmed"]
    },
    {
        "id": "misir_ali",
        "name_bn": "মিসির আলি",
        "name_en": "Misir Ali",
        "keywords_bn": [
            "মিসির আলি", "মিসির আলী", "মিসির আলির চশমা", "মিসির আলির অমিমাংসিত রহস্য",
            "মিসির আলি আপনি কোথায়", "আমিই মিসির আলি", "বাঘবন্দি মিসির আলি", "মিসির আলি unsolved", "মিসির আলি অমনিবাস"
        ],
        "keywords_en": ["misir ali", "mishir ali"],
        "author_specific_titles_bn": [
            "দেবী", "নিশীথিনী", "অন্যভুবন", "বৃহন্নলা", "ভয়", "হরতন ইশকন",
            "অমীমাংসিত রহস্য", "কুহক", "অনীশ", "বিপদ", "যমুনার জল দেখতে কালো"
        ],
        "authors": ["হুমায়ূন আহমেদ", "হুমায়ূন আহমেদ", "humayun ahmed"]
    },
    {
        "id": "shuvro",
        "name_bn": "শুভ্র",
        "name_en": "Shuvro",
        "keywords_bn": ["শুভ্র", "শুভ্র গেছে বনে", "এই শুভ্র এই", "এই শুভ্র! এই", "শুভ্র সমগ্র"],
        "keywords_en": ["shuvro", "shubhro"],
        "author_specific_titles_bn": ["দারুচিনি দ্বীপ", "মেঘের ছায়া", "মেঘের ছায়া", "রূপালী দ্বীপ"],
        "authors": ["হুমায়ূন আহমেদ", "হুমায়ূন আহমেদ", "humayun ahmed"]
    },
    {
        "id": "tenida",
        "name_bn": "টেনিদা",
        "name_en": "Tenida",
        "keywords_bn": [
            "টেনিদা", "প্যালারাম", "ক্যাবলা", "হাবুল সেন", "ঝাউবাংলোর রহস্য",
            "ঝাউ বাংলোর রহস্য", "চারমূর্তি", "কম্বল নিরুদ্দেশ", "টেনিদার অভিযান", "টেনিদা আর সিদ্ধুঘোটক", "টেনিদা সমগ্র"
        ],
        "keywords_en": ["tenida", "pyalaram", "charmurti"],
        "authors": ["নারায়ণ গঙ্গোপাধ্যায়", "নারায়ণ গঙ্গোপাধ্যায়", "narayan gangopadhyay"]
    },
    {
        "id": "ghanada",
        "name_bn": "ঘনাদা",
        "name_en": "Ghanada",
        "keywords_bn": ["ঘনাদা", "ঘনশ্যাম দাস", "ঘনাদা সমগ্র", "মঙ্গলগ্রহে ঘনাদা"],
        "keywords_en": ["ghanada", "ghana da", "ghanashyam das"],
        "authors": ["প্রেমেন্দ্র মিত্র", "premendra mitra"]
    },
    {
        "id": "rijuda",
        "name_bn": "ঋজুদা",
        "name_en": "Rijuda",
        "keywords_bn": ["ঋজুদা", "রিজুদা", "ঋজুদার সঙ্গে জঙ্গলে", "ঋজুদা সমগ্র"],
        "keywords_en": ["rijuda", "riju da", "rijudar"],
        "author_specific_titles_bn": ["বনবিবির বনে", "লবঙ্গীর জঙ্গলে", "গুগুনোগুম্বারের দেশে", "রু আহা"],
        "authors": ["বুদ্ধদেব গুহ", "buddhadeb guha"]
    },
    {
        "id": "tintin",
        "name_bn": "টিনটিন",
        "name_en": "Tintin",
        "keywords_bn": [
            "টিনটিন", "ক্যাপ্টেন হ্যাডক", "প্রফেসর ক্যালকুলাস", "আমেরিকায় টিনটিন", "ওটোকারের রাজদণ্ড", "লাল বোম্বেটের গুপ্তধন"
        ],
        "keywords_en": ["tintin"],
        "authors": ["অ্যার্জে", "হার্জ", "herge"]
    },
    {
        "id": "sherlock",
        "name_bn": "শার্লক হোমস",
        "name_en": "Sherlock Holmes",
        "keywords_bn": ["শার্লক হোমস", "শার্লক হোমসের অভিযান", "শার্লক হোমস সমগ্র"],
        "keywords_en": ["sherlock holmes"],
        "author_specific_titles_bn": ["চারের সংকেত", "রক্তাক্ত স্বাক্ষর", "বাস্কারভিলের হাউন্ড"],
        "authors": ["আর্থার কোনান ডয়েল", "আর্থার কোনান ডয়েল", "কোনান ডয়েল", "arthur conan doyle", "conan doyle"]
    },
    {
        "id": "kiriti",
        "name_bn": "কিরীটী রায়",
        "name_en": "Kiriti Roy",
        "keywords_bn": ["কিরীটী রায়", "কিরীটী সমগ্র", "কিরীটি সমগ্র", "কিরীটী", "কিরীটি রায়"],
        "keywords_en": ["kiriti roy", "kiriti"],
        "authors": ["নীহাররঞ্জন গুপ্ত", "নীহার রঞ্জন গুপ্ত", "niharranjan gupta"]
    },
    {
        "id": "shabor",
        "name_bn": "শবর দাশগুপ্ত",
        "name_en": "Shabor Dasgupta",
        "keywords_bn": ["শবর দাশগুপ্ত", "গোয়েন্দা শবর"],
        "keywords_en": ["shabor dasgupta"],
        "author_specific_titles_bn": ["ঈর্ষা", "তীরন্দাজ", "ঈগলের চোখ", "মায়ামৃগয়া", "আসছে শবর"],
        "authors": ["শীর্ষেন্দু মুখোপাধ্যায়", "শীর্ষেন্দু মুখোপাধ্যায়", "shirshendu mukhopadhyay"]
    },
    {
        "id": "taranath_tantrik",
        "name_bn": "তারানাথ তান্ত্রিক",
        "name_en": "Taranath Tantrik",
        "keywords_bn": ["তারানাথ তান্ত্রিক", "তারানাথ তান্ত্রিকের গল্প"],
        "keywords_en": ["taranath tantrik"],
        "authors": ["বিভূতিভূষণ বন্দ্যোপাধ্যায়", "তারাদাস বন্দ্যোপাধ্যায়", "তারাদাস বন্দ্যোপাধ্যায়", "taradas bandyopadhyay", "bibhutibhushan bandyopadhyay"]
    }
]


def detect_series(title: str, author: str = "") -> dict | None:
    """
    Detects if a book belongs to a prominent series based on title and author keywords.
    Uses strict boundaries to avoid false positive substring matches.
    """
    clean_title = (title or "").strip()
    clean_author = (author or "").strip().lower()
    title_lower = clean_title.lower()

    for rule in SERIES_RULES:
        rule_res = {"id": rule["id"], "name_bn": rule["name_bn"], "name_en": rule["name_en"]}

        # 1. Check title keywords (Bengali)
        for kw in rule.get("keywords_bn", []):
            if kw in clean_title:
                return rule_res

        # 2. Check title keywords (English with word boundary)
        for kw in rule.get("keywords_en", []):
            pattern = r'(?:\b|_)' + re.escape(kw.lower()) + r'(?:\b|_)'
            if re.search(pattern, title_lower):
                return rule_res

        # 3. Check author-conditional specific titles
        specific_titles = rule.get("author_specific_titles_bn", [])
        if specific_titles:
            author_matches = False
            for auth_kw in rule.get("authors", []):
                if auth_kw.lower() in clean_author:
                    author_matches = True
                    break
            if author_matches:
                base_title = re.sub(r'[\(\[\{].*?[\)\]\}]', '', clean_title).strip()
                for st in specific_titles:
                    if base_title == st or clean_title == st:
                        return rule_res
                    if len(st.split()) > 1 and st in clean_title:
                        return rule_res

    return None
