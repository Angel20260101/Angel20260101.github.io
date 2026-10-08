#!/usr/bin/env python3
"""把 content/ 下的 Markdown 筆記編譯成 dist/ 的靜態網站。

用法：python3 build.py
產出：dist/
"""

import html
import json
import re
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
STATIC = ROOT / "static"
DIST = ROOT / "dist"

MD_EXTENSIONS = ["extra", "sane_lists", "toc", "admonition"]


# --------------------------------------------------------------------------
# 讀取
# --------------------------------------------------------------------------

def load_config():
    with open(ROOT / "site.json", encoding="utf-8") as f:
        return json.load(f)


def parse_front_matter(text):
    """解析檔案開頭以 --- 包住的 key: value 區塊。"""
    meta = {}
    if not text.startswith("---"):
        return meta, text
    end = text.find("\n---", 3)
    if end == -1:
        return meta, text
    block = text[3:end]
    body = text[end + 4:].lstrip("\n")
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, body


def load_articles(config):
    """讀出所有文章，依系列分組並排序。"""
    by_series = {}
    for series in config["series"]:
        slug = series["slug"]
        folder = CONTENT / slug
        articles = []
        if not folder.is_dir():
            by_series[slug] = articles
            continue
        for path in sorted(folder.glob("*.md")):
            raw = path.read_text(encoding="utf-8")
            meta, body = parse_front_matter(raw)
            if meta.get("draft", "").lower() == "true":
                continue
            articles.append({
                "slug": path.stem,
                "series": slug,
                "title": meta.get("title", path.stem),
                "category": meta.get("category", ""),
                "date": meta.get("date", ""),
                "summary": meta.get("summary", ""),
                "order": int(meta["order"]) if meta.get("order", "").isdigit() else 9999,
                "source": meta.get("source", ""),
                "body": body,
                "url": f"/{slug}/{path.stem}/",
            })

        order_of = {name: i for i, name in enumerate(series.get("categories", []))}
        articles.sort(key=lambda a: (order_of.get(a["category"], 999), a["order"], a["slug"]))
        for i, article in enumerate(articles):
            article["prev"] = articles[i - 1] if i > 0 else None
            article["next"] = articles[i + 1] if i < len(articles) - 1 else None
        by_series[slug] = articles
    return by_series


# --------------------------------------------------------------------------
# 樣板
# --------------------------------------------------------------------------

def e(text):
    return html.escape(str(text or ""))


def page(config, *, title, body, description="", depth=1, active=""):
    """包上完整的 HTML 骨架。depth 用來決定 CSS 的相對路徑。"""
    css = "../" * depth + "style.css"
    site_title = config["title"]
    full_title = site_title if title == site_title else f"{title}｜{site_title}"
    home = "../" * depth or "./"
    nav = "".join(
        '<a href="{href}"{cls}>{label}</a>'.format(
            href=f'{home}{s["slug"]}/',
            cls=' class="active"' if s["slug"] == active else "",
            label=e(s["title"]),
        )
        for s in config["series"]
    )
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(description or config.get('tagline', ''))}">
<link rel="stylesheet" href="{css}">
</head>
<body>
<header class="site-header">
  <a class="site-name" href="{home}">{e(site_title)}</a>
  <nav class="site-nav">{nav}</nav>
</header>
<main>
{body}
</main>
<footer class="site-footer">
  <p>{e(config.get('footer', ''))}</p>
</footer>
</body>
</html>
"""


def article_card(article, prefix=""):
    summary = (
        f'<p class="card-summary">{e(article["summary"])}</p>' if article["summary"] else ""
    )
    date = f'<time>{e(article["date"])}</time>' if article["date"] else ""
    return f"""<li class="card">
  <a href="{prefix}{e(article["slug"])}/">
    <h3>{e(article["title"])}</h3>
    {summary}
    <div class="card-meta">{date}</div>
  </a>
</li>"""


def grouped_list(series, articles, prefix=""):
    """依類別分組列出文章。"""
    if not articles:
        return '<p class="empty">這個系列還沒有文章。</p>'
    blocks = []
    categories = series.get("categories", []) or sorted({a["category"] for a in articles})
    for category in categories:
        items = [a for a in articles if a["category"] == category]
        if not items:
            continue
        cards = "\n".join(article_card(a, prefix) for a in items)
        blocks.append(f"""<section class="group">
  <h2 class="group-title">{e(category)}<span class="group-count">{len(items)}</span></h2>
  <ul class="cards">
{cards}
  </ul>
</section>""")
    leftovers = [a for a in articles if a["category"] not in categories]
    if leftovers:
        cards = "\n".join(article_card(a, prefix) for a in leftovers)
        blocks.append(f'<section class="group">\n  <ul class="cards">\n{cards}\n  </ul>\n</section>')
    return "\n".join(blocks)


# --------------------------------------------------------------------------
# 產生頁面
# --------------------------------------------------------------------------

def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_home(config, by_series):
    sections = []
    for series in config["series"]:
        articles = by_series[series["slug"]]
        sections.append(f"""<section class="series-block">
  <h2 class="series-title"><a href="{e(series["slug"])}/">{e(series["title"])}</a></h2>
  <p class="series-desc">{e(series.get("description", ""))}</p>
  {grouped_list(series, articles, prefix=f'{series["slug"]}/')}
</section>""")
    body = f"""<div class="hero">
  <h1>{e(config["title"])}</h1>
  <p class="tagline">{e(config.get("tagline", ""))}</p>
</div>
{"".join(sections)}"""
    write(DIST / "index.html", page(config, title=config["title"], body=body, depth=0))


def build_series(config, by_series):
    for series in config["series"]:
        articles = by_series[series["slug"]]
        body = f"""<div class="page-head">
  <h1>{e(series["title"])}</h1>
  <p class="tagline">{e(series.get("description", ""))}</p>
  <p class="count">共 {len(articles)} 篇</p>
</div>
{grouped_list(series, articles)}"""
        write(
            DIST / series["slug"] / "index.html",
            page(
                config,
                title=series["title"],
                description=series.get("description", ""),
                body=body,
                depth=1,
                active=series["slug"],
            ),
        )


def build_articles(config, by_series):
    for series in config["series"]:
        for article in by_series[series["slug"]]:
            md = markdown.Markdown(extensions=MD_EXTENSIONS)
            content = md.convert(article["body"])

            meta_bits = []
            if article["category"]:
                meta_bits.append(f'<span class="tag">{e(article["category"])}</span>')
            if article["date"]:
                meta_bits.append(f'<time>{e(article["date"])}</time>')
            meta = f'<div class="article-meta">{"".join(meta_bits)}</div>'

            nav = []
            if article["prev"]:
                nav.append(
                    f'<a class="prev" href="../{e(article["prev"]["slug"])}/">'
                    f'<span>上一篇</span>{e(article["prev"]["title"])}</a>'
                )
            if article["next"]:
                nav.append(
                    f'<a class="next" href="../{e(article["next"]["slug"])}/">'
                    f'<span>下一篇</span>{e(article["next"]["title"])}</a>'
                )
            nav_html = f'<nav class="article-nav">{"".join(nav)}</nav>' if nav else ""

            source = ""
            if article["source"]:
                source = (
                    f'<p class="source">課程連結：'
                    f'<a href="{e(article["source"])}" rel="noopener">{e(article["source"])}</a></p>'
                )

            body = f"""<article>
  <div class="article-head">
    <p class="breadcrumb"><a href="../">{e(series["title"])}</a></p>
    <h1>{e(article["title"])}</h1>
    {meta}
  </div>
  <div class="prose">
{content}
  </div>
  {source}
</article>
{nav_html}"""
            write(
                DIST / series["slug"] / article["slug"] / "index.html",
                page(
                    config,
                    title=article["title"],
                    description=article["summary"],
                    body=body,
                    depth=2,
                    active=series["slug"],
                ),
            )


def build_404(config):
    body = """<div class="page-head">
  <h1>找不到這個頁面</h1>
  <p class="tagline">網址可能打錯了，或這篇筆記還沒發布。</p>
  <p><a href="/">回首頁</a></p>
</div>"""
    write(DIST / "404.html", page(config, title="找不到頁面", body=body, depth=0))


def main():
    config = load_config()
    by_series = load_articles(config)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    for item in STATIC.iterdir() if STATIC.is_dir() else []:
        if item.is_file():
            shutil.copy2(item, DIST / item.name)
        else:
            shutil.copytree(item, DIST / item.name)

    # 讓 GitHub Pages 原樣提供檔案，不要再跑一次 Jekyll
    (DIST / ".nojekyll").write_text("", encoding="utf-8")

    build_home(config, by_series)
    build_series(config, by_series)
    build_articles(config, by_series)
    build_404(config)

    total = sum(len(v) for v in by_series.values())
    print(f"完成：{total} 篇文章，{len(config['series'])} 個系列 → {DIST}")


if __name__ == "__main__":
    main()
