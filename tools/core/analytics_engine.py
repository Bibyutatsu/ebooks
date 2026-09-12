"""
Scalable Analytics & Similarity Graph Engine for Bibyutatsu BookStore.

Computes:
1. Per-Book Analytics & Similarity:
   - Multi-factor related books recommendation (series continuity, author affinity, shared genres Jaccard index, phonetic title tokens).
2. Per-Author Analytics & Affinity:
   - Author catalog metrics (total books, formats breakdown, genre distributions).
   - Author similarity/co-affinity (shared genres, thematic clusters, shared series).
3. Per-Series Analytics:
   - Canonical reading order, completeness, genre distribution.
4. Graph Serialization:
   - Exports analytics/catalog_graph.json and analytics/summary.json for downstream caching,
     future vector/embedding search, and recommendation APIs.
"""

import os
import re
import json
import unicodedata
from pathlib import Path
from collections import Counter, defaultdict


def slugify(text: str, max_len: int = 60) -> str:
    """Creates a clean URL-safe lowercase ASCII slug, capped to max_len."""
    text = unicodedata.normalize('NFKD', str(text or ''))
    text = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '-', text).strip('-')
    if len(slug) > max_len:
        parts = slug[:max_len].rsplit('-', 1)
        slug = parts[0] if parts[0] else slug[:max_len]
    return slug or f"item-{abs(hash(str(text))) % 100000}"


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """Computes Jaccard similarity between two sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


class AnalyticsEngine:
    def __init__(self, catalog_path_or_dict):
        if isinstance(catalog_path_or_dict, (str, Path)):
            with open(catalog_path_or_dict, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = catalog_path_or_dict

        self.books = self.data.get("books", [])
        self.books_by_id = {b["id"]: b for b in self.books}
        
        # Inverted index mappings
        self.author_to_books = defaultdict(list)
        self.series_to_books = defaultdict(list)
        self.genre_to_books = defaultdict(list)
        self.book_tokens = {}
        self.author_info_map = {}
        
        self._build_indexes()

    def _build_indexes(self):
        """Builds in-memory inverted indexes for sub-millisecond similarity scoring."""
        for b in self.books:
            b_id = b["id"]
            author = b.get("author", "").strip()
            if author:
                self.author_to_books[author].append(b_id)
                if author not in self.author_info_map:
                    self.author_info_map[author] = {
                        "name_bn": author,
                        "name_en": b.get("author_en", author),
                        "aliases": b.get("author_aliases", [])
                    }

            series = b.get("series")
            if series and isinstance(series, dict) and series.get("id"):
                s_id = series["id"]
                self.series_to_books[s_id].append(b_id)

            for g in b.get("genres", []):
                self.genre_to_books[g.strip()].append(b_id)

            # Pre-tokenize title and transliterations for Jaccard matching
            tokens = set()
            if b.get("title_en"):
                tokens.update(b["title_en"].lower().split())
            for t in b.get("title_translit", []):
                tokens.update(t.lower().split())
            self.book_tokens[b_id] = tokens

    def get_related_books(self, book_id: str, limit: int = 6) -> list[dict]:
        """
        Calculates top related books using multi-factor affinity scoring:
        - Same series: +50 pts (preserves narrative universe)
        - Same author: +25 pts
        - Shared genres Jaccard index: up to +20 pts
        - Phonetic title token overlap: up to +15 pts
        """
        target = self.books_by_id.get(book_id)
        if not target:
            return []

        target_series_id = None
        if target.get("series") and isinstance(target["series"], dict):
            target_series_id = target["series"].get("id")

        target_author = target.get("author")
        target_genres = set(target.get("genres", []))
        target_tokens = self.book_tokens.get(book_id, set())

        candidate_ids = set()
        # Candidate generation: only score plausible candidates from same series, author, or genres
        if target_series_id and target_series_id in self.series_to_books:
            candidate_ids.update(self.series_to_books[target_series_id])
        if target_author and target_author in self.author_to_books:
            candidate_ids.update(self.author_to_books[target_author])
        for g in target_genres:
            # Add up to 50 sample candidates from same genres
            candidate_ids.update(self.genre_to_books[g][:50])

        candidate_ids.discard(book_id)

        scored = []
        for c_id in candidate_ids:
            cand = self.books_by_id[c_id]
            score = 0.0

            # 1. Series affinity
            cand_series_id = None
            if cand.get("series") and isinstance(cand["series"], dict):
                cand_series_id = cand["series"].get("id")

            if target_series_id and cand_series_id == target_series_id:
                score += 50.0

            # 2. Author affinity
            if target_author and cand.get("author") == target_author:
                score += 25.0

            # 3. Genre Jaccard
            cand_genres = set(cand.get("genres", []))
            g_sim = jaccard_similarity(target_genres, cand_genres)
            score += g_sim * 20.0

            # 4. Title token overlap
            cand_tokens = self.book_tokens.get(c_id, set())
            t_sim = jaccard_similarity(target_tokens, cand_tokens)
            score += t_sim * 15.0

            scored.append((score, cand))

        # Sort descending by score, tie-break by year/title
        scored.sort(key=lambda x: (x[0], x[1].get("year", ""), x[1].get("title", "")), reverse=True)

        results = []
        for sc, b in scored[:limit]:
            results.append({
                "id": b["id"],
                "title": b["title"],
                "title_en": b.get("title_en", ""),
                "author": b["author"],
                "author_en": b.get("author_en", ""),
                "cover": b.get("cover", ""),
                "year": b.get("year", ""),
                "score": round(sc, 2),
                "formats": list(b.get("formats", {}).keys()),
                "series": b.get("series")
            })

        return results

    def compute_author_analytics(self) -> dict[str, dict]:
        """
        Computes detailed analytics for every author:
        - Total books, format breakdown, genre breakdown.
        - Associated series.
        - Similar authors based on shared genres and series themes.
        """
        author_data = {}
        all_authors = list(self.author_to_books.keys())

        # Build author genre profiles for similarity
        author_genre_profiles = {}
        for author, b_ids in self.author_to_books.items():
            genre_counts = Counter()
            for b_id in b_ids:
                for g in self.books_by_id[b_id].get("genres", []):
                    genre_counts[g] += 1
            author_genre_profiles[author] = set(genre_counts.keys())

        # Pre-assign unique bounded slugs for all authors
        self.author_slugs = {}
        used_slugs = set()
        for author in all_authors:
            info = self.author_info_map.get(author, {})
            name_en = info.get("name_en", author)
            base_slug = slugify(name_en, max_len=50) if name_en else slugify(author, max_len=50)
            slug = base_slug
            counter = 1
            while slug in used_slugs:
                slug = f"{base_slug[:45]}-{counter}"
                counter += 1
            used_slugs.add(slug)
            self.author_slugs[author] = slug

        for author, b_ids in self.author_to_books.items():
            info = self.author_info_map.get(author, {})
            name_en = info.get("name_en", author)
            slug = self.author_slugs[author]

            genre_counts = Counter()
            format_counts = Counter()
            series_set = {}
            total_size_bytes = 0

            for b_id in b_ids:
                b = self.books_by_id[b_id]
                for g in b.get("genres", []):
                    genre_counts[g] += 1
                for fmt, f_info in b.get("formats", {}).items():
                    format_counts[fmt] += 1
                    total_size_bytes += f_info.get("size_bytes", 0)
                if b.get("series") and isinstance(b["series"], dict):
                    s = b["series"]
                    series_set[s["id"]] = {"id": s["id"], "name_bn": s.get("name_bn"), "name_en": s.get("name_en")}

            # Find similar authors based on genre overlap
            my_genres = author_genre_profiles.get(author, set())
            similar_candidates = []
            for other_author in all_authors:
                if other_author == author or len(self.author_to_books[other_author]) < 2:
                    continue
                other_genres = author_genre_profiles.get(other_author, set())
                sim = jaccard_similarity(my_genres, other_genres)
                if sim > 0:
                    other_info = self.author_info_map.get(other_author, {})
                    other_en = other_info.get("name_en", other_author)
                    other_slug = self.author_slugs[other_author]
                    similar_candidates.append({
                        "name_bn": other_author,
                        "name_en": other_en,
                        "slug": other_slug,
                        "similarity": round(sim, 2),
                        "books_count": len(self.author_to_books[other_author])
                    })

            similar_candidates.sort(key=lambda x: (x["similarity"], x["books_count"]), reverse=True)

            author_data[slug] = {
                "slug": slug,
                "name_bn": author,
                "name_en": name_en,
                "aliases": info.get("aliases", []),
                "total_books": len(b_ids),
                "book_ids": b_ids,
                "genres": dict(genre_counts.most_common()),
                "formats": dict(format_counts),
                "series": list(series_set.values()),
                "total_size_bytes": total_size_bytes,
                "similar_authors": similar_candidates[:5]
            }

        return author_data

    def compute_series_analytics(self) -> dict[str, dict]:
        """
        Computes detailed analytics for every series:
        - Reading order, creator/author, genres, total books.
        """
        series_data = {}
        for s_id, b_ids in self.series_to_books.items():
            books_in_series = [self.books_by_id[b_id] for b_id in b_ids]
            
            # Sort reading order: by year first if available, otherwise by title
            books_in_series.sort(key=lambda x: (x.get("year", "9999"), x.get("title", "")))

            first_book = books_in_series[0]
            s_obj = first_book.get("series", {})
            name_bn = s_obj.get("name_bn", s_id)
            name_en = s_obj.get("name_en", s_id.replace("_", " ").title())

            author = first_book.get("author")
            author_en = first_book.get("author_en")

            genre_counts = Counter()
            format_counts = Counter()
            for b in books_in_series:
                for g in b.get("genres", []):
                    genre_counts[g] += 1
                for fmt in b.get("formats", {}):
                    format_counts[fmt] += 1

            series_data[s_id] = {
                "id": s_id,
                "slug": slugify(s_id),
                "name_bn": name_bn,
                "name_en": name_en,
                "author": author,
                "author_en": author_en,
                "author_slug": slugify(author_en or author),
                "total_books": len(books_in_series),
                "book_ids": [b["id"] for b in books_in_series],
                "genres": dict(genre_counts.most_common()),
                "formats": dict(format_counts)
            }

        return series_data

    def export_graph(self, output_dir: str = "analytics") -> tuple[dict, dict]:
        """
        Generates and writes:
        - analytics/catalog_graph.json (full relational graph)
        - analytics/summary.json (lightweight high-level metrics)
        """
        os.makedirs(output_dir, exist_ok=True)

        authors_data = self.compute_author_analytics()
        series_data = self.compute_series_analytics()

        # Compute book relations graph
        book_relations = {}
        for b in self.books:
            book_relations[b["id"]] = self.get_related_books(b["id"], limit=6)

        total_formats = Counter()
        total_genres = Counter()
        for b in self.books:
            for fmt in b.get("formats", {}):
                total_formats[fmt] += 1
            for g in b.get("genres", []):
                total_genres[g] += 1

        summary = {
            "version": "1.0.0",
            "total_books": len(self.books),
            "total_authors": len(authors_data),
            "total_series": len(series_data),
            "format_breakdown": dict(total_formats),
            "top_genres": dict(total_genres.most_common(20)),
            "top_authors": [
                {"name_bn": a["name_bn"], "name_en": a["name_en"], "slug": a["slug"], "count": a["total_books"]}
                for a in sorted(authors_data.values(), key=lambda x: x["total_books"], reverse=True)[:30]
            ],
            "series_list": [
                {"id": s["id"], "slug": s["slug"], "name_bn": s["name_bn"], "name_en": s["name_en"], "count": s["total_books"]}
                for s in sorted(series_data.values(), key=lambda x: x["total_books"], reverse=True)
            ]
        }

        full_graph = {
            "summary": summary,
            "authors": authors_data,
            "series": series_data,
            "book_relations": book_relations
        }

        graph_file = Path(output_dir) / "catalog_graph.json"
        with open(graph_file, "w", encoding="utf-8") as f:
            json.dump(full_graph, f, ensure_ascii=False, indent=2)

        summary_file = Path(output_dir) / "summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"✓ Analytics graph exported to {graph_file} ({len(self.books)} books, {len(authors_data)} authors, {len(series_data)} series).")
        print(f"✓ Summary exported to {summary_file}.")

        return summary, full_graph


if __name__ == "__main__":
    catalog_path = Path(__file__).resolve().parent.parent.parent / "catalog.json"
    engine = AnalyticsEngine(catalog_path)
    engine.export_graph()
