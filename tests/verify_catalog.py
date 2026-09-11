"""
Comprehensive verification and test suite for the ebooks catalog.
Validates:
1. Schema integrity, metadata standardization, and format consistency.
2. Search & transliteration recall across 40+ English & Bengali test queries.
3. Fuzzy tolerance for typos and phonetic variations.
"""

import json
import os
import sys
from pathlib import Path


def levenshtein_distance(s1: str, s2: str) -> int:
    """Computes standard Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def fuzzy_match_token(query_token: str, target_tokens: list[str], max_dist: int = 2) -> bool:
    """Checks if query token matches any target token exactly, as prefix, or within max_dist."""
    q = query_token.lower()
    for t in target_tokens:
        t_low = t.lower()
        if q in t_low or t_low.startswith(q):
            return True
        if len(q) >= 4 and abs(len(q) - len(t_low)) <= max_dist:
            if levenshtein_distance(q, t_low) <= max_dist:
                return True
    return False


def test_schema_and_integrity(catalog_path: str):
    """Validates structural integrity and standardization of the catalog."""
    print("========================================")
    print("RUNNING SCHEMA & INTEGRITY VERIFICATION")
    print("========================================")

    assert os.path.exists(catalog_path), f"Catalog file not found: {catalog_path}"
    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Top-level keys: books and version are required
    for key in ("version", "books"):
        assert key in data, f"Missing top-level key: {key}"

    books = data["books"]
    assert len(books) > 0, "Catalog contains 0 books"

    # Derive runtime stats from books
    author_set = set(b.get("author") for b in books if b.get("author"))
    format_counts = {}
    for b in books:
        for fmt in b.get("formats", {}):
            format_counts[fmt] = format_counts.get(fmt, 0) + 1

    print(f"✓ Validated: {len(books)} books, {len(author_set)} authors.")
    print(f"✓ Formats verified: {format_counts}")

    # Validate individual books
    valid_formats = { "epub", "kfx", "mobi", "pdf", "docx", "txt", "azw3", "external" }
    id_set = set()

    for idx, book in enumerate(data["books"]):
        b_id = book.get("id")
        assert b_id, f"Book at index {idx} has no id"
        assert b_id not in id_set, f"Duplicate book id: {b_id}"
        id_set.add(b_id)

        assert book.get("title"), f"Book {b_id} missing Bengali title"
        assert book.get("title_en"), f"Book {b_id} missing English title"
        assert book.get("author"), f"Book {b_id} missing Bengali author"
        assert book.get("author_en"), f"Book {b_id} missing English author"
        assert book.get("formats"), f"Book {b_id} has no available formats"

        # Check format fields
        for fmt, info in book["formats"].items():
            assert fmt in valid_formats, f"Invalid format {fmt} in book {b_id}"
            assert info.get("filename"), f"Missing filename for {fmt} in {b_id}"
            if info.get("source") not in ("wikisource", "archive_org", "eboipotro") and not info.get("download_url", "").startswith("https://ws-export"):
                assert info.get("size_bytes", 0) > 0, f"Zero byte size for {fmt} in {b_id}"
            assert info.get("size_formatted"), f"Missing formatted size in {b_id}"

        # Check search text
        assert book.get("search_text"), f"Missing pre-computed search_text for {b_id}"

    print(f"✓ Verified 100% of {len(data['books'])} books conform to normalized schema.")


def test_search_and_transliteration(catalog_path: str):
    """
    Tests search recall using English transliterated queries,
    author aliases, series names, and typo variations.
    """
    print("\n========================================")
    print("RUNNING TRANSLITERATION & SEARCH BENCHMARKS")
    print("========================================")

    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    books = data["books"]

    # Benchmark test cases: (query, min_expected_matches, description)
    benchmark_queries = [
        # Iconic characters & series
        ("feluda", 5, "Feluda detective series"),
        ("sonar kella", 1, "Sonar Kella title in English"),
        ("byomkesh", 5, "Byomkesh Bakshi mystery series"),
        ("bomkesh", 5, "Byomkesh colloquial phonetic variant"),
        ("satyanweshi", 1, "Satyanweshi Byomkesh title"),
        ("shonku", 3, "Professor Shonku sci-fi stories"),
        ("kakababu", 1, "Kakababu adventure series"),
        ("tin goyenda", 3, "Tin Goyenda (Three Detectives)"),
        ("masud rana", 5, "Masud Rana spy thriller series"),
        ("himu", 5, "Himu novel series by Humayun Ahmed"),
        ("misir ali", 3, "Misir Ali psychological mystery"),
        ("tenida", 1, "Tenida humor stories"),
        ("tintin", 1, "Tintin comics translated by Hergé"),
        ("sherlock holmes", 1, "Sherlock Holmes Arthur Conan Doyle"),

        # Bengali Authors searched in English
        ("satyajit ray", 10, "Satyajit Ray author query"),
        ("satyajit roy", 10, "Satyajit Roy spelling variant"),
        ("humayun ahmed", 20, "Humayun Ahmed author query"),
        ("humayan ahmed", 20, "Humayan Ahmed typo/variation"),
        ("sharadindu bandyopadhyay", 5, "Sharadindu Bandyopadhyay"),
        ("sharadindu banerjee", 5, "Sharadindu Banerjee English alias"),
        ("sunil gangopadhyay", 5, "Sunil Gangopadhyay author query"),
        ("sunil ganguly", 5, "Sunil Ganguly English alias"),
        ("shirshendu mukhopadhyay", 5, "Shirshendu Mukhopadhyay"),
        ("sirshendu", 5, "Sirshendu phonetic query"),
        ("bibhutibhushan bandyopadhyay", 5, "Bibhutibhushan Bandyopadhyay"),
        ("bibhutibhushan banerjee", 5, "Bibhutibhushan Banerjee English alias"),
        ("chander pahar", 1, "Chander Pahar adventure novel"),
        ("atin bandyopadhyay", 2, "Atin Bandyopadhyay query"),
        ("atin banerjee", 2, "Atin Banerjee English alias"),
        ("samaresh majumdar", 5, "Samaresh Majumdar author query"),
        ("buddhadeb guha", 5, "Buddhadeb Guha author query"),
        ("zafar iqbal", 5, "Zafar Iqbal sci-fi author"),
        ("sukumar ray", 1, "Sukumar Ray author query"),
        ("shibram chakraborty", 1, "Shibram Chakraborty humor"),

        # World literature in Bengali
        ("agatha christie", 5, "Agatha Christie translated novels"),
        ("jules verne", 5, "Jules Verne translated sci-fi"),
        ("stephen king", 1, "Stephen King translated horror"),
        ("edgar allan poe", 1, "Edgar Allan Poe translated classics"),
        ("keigo higashino", 2, "Keigo Higashino Japanese mystery"),
        ("asimov", 1, "Isaac Asimov sci-fi in Bangla"),
        ("herge", 5, "Hergé Tintin author search"),

        # Bengali Script Direct Searches
        ("ফেলুদা", 5, "Feluda in Bengali Unicode"),
        ("ব্যোমকেশ", 5, "Byomkesh in Bengali Unicode"),
        ("হুমায়ূন আহমেদ", 20, "Humayun Ahmed in Bengali Unicode"),
        ("সত্যজিৎ রায়", 10, "Satyajit Ray in Bengali Unicode"),
        ("তিতাস একটি নদীর নাম", 1, "Titas Ekti Nadir Naam in Bengali"),
        ("ঈশ্বরচন্দ্র বিদ্যাসাগর", 3, "Ishwar Chandra Vidyasagar in Bengali Unicode"),
        ("vidyasagar", 3, "Ishwar Chandra Vidyasagar English search"),
        ("abanindranath", 3, "Abanindranath Tagore English search"),
        ("ক্ষীরের পুতুল", 1, "Khirer Putul classic children tale"),
        ("madhusudan dutt", 2, "Michael Madhusudan Dutt epic poet"),
        ("begum rokeya", 1, "Begum Rokeya feminist pioneer"),
        ("rakhaldas banerjee", 2, "Rakhaldas Bandyopadhyay archaeologist"),
    ]

    total_benchmarks = len(benchmark_queries)
    passed_benchmarks = 0

    for query, min_expected, desc in benchmark_queries:
        q_tokens = [w for w in query.lower().split() if w]
        matches = []

        for book in books:
            st = book["search_text"].lower()
            target_tokens = st.split()
            # All query tokens must match either exactly, prefix, or fuzzy
            all_matched = True
            for q_tok in q_tokens:
                if not fuzzy_match_token(q_tok, target_tokens, max_dist=2):
                    all_matched = False
                    break
            if all_matched:
                matches.append(book)

        count = len(matches)
        if count >= min_expected:
            passed_benchmarks += 1
            print(f"  [PASS] '{query}' -> Found {count} books (expected >={min_expected}) | {desc}")
        else:
            print(f"  [FAIL] '{query}' -> Found {count} books (expected >={min_expected}) | {desc}")

    print("----------------------------------------")
    print(f"Benchmark Results: {passed_benchmarks}/{total_benchmarks} passed ({(passed_benchmarks/total_benchmarks)*100:.1f}%)")
    assert passed_benchmarks == total_benchmarks, f"Search benchmark failure: {passed_benchmarks}/{total_benchmarks} passed."
    print("✓ All search and transliteration benchmarks PASSED with 100% recall!")


if __name__ == "__main__":
    catalog_path = sys.argv[1] if len(sys.argv) > 1 else "./ebooks/catalog.json"
    try:
        test_schema_and_integrity(catalog_path)
        test_search_and_transliteration(catalog_path)
        print("\n🎉 ALL VERIFICATION CHECKS COMPLETED SUCCESSFULLY!")
    except AssertionError as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        sys.exit(1)
