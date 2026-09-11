"""
Rules and keywords to automatically detect popular Bengali literary series and characters.
"""

SERIES_RULES = [
    {
        "id": "feluda",
        "name_bn": "ফেলুদা",
        "name_en": "Feluda",
        "keywords_bn": ["ফেলুদা", "তোপসে", "জটায়ু", "লালমোহন", "সোনার কেল্লা", "জয়বাবা ফেলুনাথ", "বাদশাহী আংটি", "বোম্বাইয়ের বোম্বেটে", "টিনটোরেটোর যীশু", "কৈলাসে কেলেঙ্কারী", "গোরস্থানে সাবধান", "রয়েল বেঙ্গল রহস্য", "ছিন্নমস্তার অভিশাপ", "গোলাপি মুক্তা"],
        "keywords_en": ["feluda", "topshe", "jatayu", "lalmohan ganguly", "sonar kella", "badsahi angti"]
    },
    {
        "id": "byomkesh",
        "name_bn": "ব্যোমকেশ বক্সী",
        "name_en": "Byomkesh Bakshi",
        "keywords_bn": ["ব্যোমকেশ", "বোমক্যাশ", "সত্যান্বেষী", "অজিত", "দুর্গরহস্য", "সজারুর কাঁটা", "অর্থমনর্থম", "চিত্রচোর", "আদিম রিপু", "বেণীসংহার", "লোহার বিস্কুট"],
        "keywords_en": ["byomkesh", "bomkesh", "satyanweshi", "byomkesh bakshi", "ajit", "durgo rahasya"]
    },
    {
        "id": "shonku",
        "name_bn": "প্রফেসর শঙ্কু",
        "name_en": "Professor Shonku",
        "keywords_bn": ["শঙ্কু", "প্রফেসর শঙ্কু", "করভাস", "কম্পু", "মিরাকিউরল", "একশৃঙ্গ অভিযান", "নকুড়বাবু ও এল ডোরাডো", "মরু রহস্য"],
        "keywords_en": ["shonku", "professor shonku", "prof shanku", "shanku", "corvus"]
    },
    {
        "id": "kakababu",
        "name_bn": "কাকাবাবু",
        "name_en": "Kakababu",
        "keywords_bn": ["কাকাবাবু", "রাজা রায়চৌধুরী", "সন্তু", "পাহাড়চূড়ায় আতঙ্ক", "সবুজ দ্বীপের রাজা", "ভূপাল রহস্য", "মিশর রহস্য", "জঙ্গলের মধ্যে এক হোটেল"],
        "keywords_en": ["kakababu", "santu", "mishor rahasya", "sabuj dwiper raja"]
    },
    {
        "id": "masud_rana",
        "name_bn": "মাসুদ রানা",
        "name_en": "Masud Rana",
        "keywords_bn": ["মাসুদ রানা", "রানা", "ধ্বংস পাহাড়", "ভারতনাট্যম", "স্বর্ণমৃগ"],
        "keywords_en": ["masud rana", "rana", "major rana"]
    },
    {
        "id": "tin_goyenda",
        "name_bn": "তিন গোয়েন্দা",
        "name_en": "Tin Goyenda (Three Detectives)",
        "keywords_bn": ["তিন গোয়েন্দা", "তিন গোয়েন্দা", "কিশোর পাশা", "মুসা আমান", "রবিন মিলফোর্ড"],
        "keywords_en": ["tin goyenda", "teen goyenda", "three detectives", "kishore pasha", "musa aman", "robin milford"]
    },
    {
        "id": "himu",
        "name_bn": "হিমু",
        "name_en": "Himu",
        "keywords_bn": ["হিমু", "হলুদ হিমু", "ময়ূরাক্ষী", "দরজার ওপাশে", "হিমুর হাতে কয়েকটি নীলপদ্ম", "হিমুর দ্বিতীয় প্রহর", "আঙুল কাটা জগলু", "আজ হিমুর বিয়ে"],
        "keywords_en": ["himu", "holud himu", "mayurakkhi", "himur"]
    },
    {
        "id": "misir_ali",
        "name_bn": "মিসির আলি",
        "name_en": "Misir Ali",
        "keywords_bn": ["মিসির আলি", "মিসির আলী", "দেবী", "নিশীথিনী", "অন্যভুবন", "বৃহন্নলা", "ভয়", "অমিমাংসিত রহস্য"],
        "keywords_en": ["misir ali", "mishir ali", "devi", "nishithini"]
    },
    {
        "id": "shuvro",
        "name_bn": "শুভ্র",
        "name_en": "Shuvro",
        "keywords_bn": ["শুভ্র", "দারুচিনি দ্বীপ", "মেঘের ছায়া", "রূপালী দ্বীপ"],
        "keywords_en": ["shuvro", "shubhro", "daruchini dwip"]
    },
    {
        "id": "tenida",
        "name_bn": "টেনিদা",
        "name_en": "Tenida",
        "keywords_bn": ["টেনিদা", "প্যালারাম", "ক্যাবলা", "হাবুল সেন", "ঝাউবাংলোর রহস্য", "চারমূর্তি", "কম্বল নিরুদ্দেশ"],
        "keywords_en": ["tenida", "pyalaram", "charmurti"]
    },
    {
        "id": "ghanada",
        "name_bn": "ঘনাদা",
        "name_en": "Ghanada",
        "keywords_bn": ["ঘনাদা", "ঘনশ্যাম দাস", "মেসবাড়ি"],
        "keywords_en": ["ghanada", "ghana da", "ghanashyam das"]
    },
    {
        "id": "rijuda",
        "name_bn": "রিজুদা",
        "name_en": "Rijuda",
        "keywords_bn": ["রিজুদা", "রুদ্র", "টিটো"],
        "keywords_en": ["rijuda", "riju da", "rudra"]
    },
    {
        "id": "tintin",
        "name_bn": "টিনটিন",
        "name_en": "Tintin",
        "keywords_bn": ["টিনটিন", "ক্যাপ্টেন হ্যাডক", "প্রফেসর ক্যালকুলাস", "স্নোয়ি", "নীলকমল", "মমির অভিশাপ", "আমেরিকায় টিনটিন", "ওটোকারের রাজদণ্ড", "লাল বোম্বেটের গুপ্তধন"],
        "keywords_en": ["tintin", "captain haddock", "snowy", "calculus", "blue lotus", "red rackham"]
    },
    {
        "id": "sherlock",
        "name_bn": "শার্লক হোমস",
        "name_en": "Sherlock Holmes",
        "keywords_bn": ["শার্লক হোমস", "শার্লক", "হোমস", "ডক্টর ওয়াটসন", "চারের সংকেত", "রক্তাক্ত স্বাক্ষর", "বাস্কারভিলের হাউন্ড"],
        "keywords_en": ["sherlock holmes", "sherlock", "holmes", "dr watson", "hound of the baskervilles"]
    },
    {
        "id": "kiriti",
        "name_bn": "কিরীটী রায়",
        "name_en": "Kiriti Roy",
        "keywords_bn": ["কিরীটী", "কিরীটি", "সুব্রত"],
        "keywords_en": ["kiriti roy", "kiriti", "subrata"]
    },
    {
        "id": "shabor",
        "name_bn": "শবর দাশগুপ্ত",
        "name_en": "Shabor Dasgupta",
        "keywords_bn": ["শবর দাশগুপ্ত", "গোয়েন্দা শবর", "ঈর্ষা", "তীরন্দাজ", "ঋণ"],
        "keywords_en": ["shabor dasgupta", "shabor", "eagoler chokh"]
    }
]


def detect_series(title: str, author: str = "") -> dict | None:
    """
    Detects if a book belongs to a prominent series based on title and author keywords.
    """
    text = f"{title} {author}".lower()
    for rule in SERIES_RULES:
        for kw in rule["keywords_bn"]:
            if kw.lower() in text:
                return {"id": rule["id"], "name_bn": rule["name_bn"], "name_en": rule["name_en"]}
        for kw in rule["keywords_en"]:
            if kw.lower() in text:
                return {"id": rule["id"], "name_bn": rule["name_bn"], "name_en": rule["name_en"]}
    return None
