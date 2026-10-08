# Angel 的學習筆記

個人學習筆記網站，用 Markdown 寫、自動部署到 GitHub Pages。

網址：https://angel20260101.github.io/

## 怎麼新增一篇筆記

在 `content/<系列資料夾>/` 新增一個 `.md` 檔，開頭放設定區塊：

```markdown
---
title: 文章標題
category: 核心
order: 1
date: 2026-10-08
summary: 一句話摘要，會顯示在列表上
---

正文從這裡開始。
```

| 欄位 | 必填 | 說明 |
| --- | --- | --- |
| `title` | 是 | 文章標題 |
| `category` | 是 | 要是該系列在 `site.json` 裡定義的分類之一 |
| `order` | 否 | 同分類內的排序，數字小的在前 |
| `date` | 否 | 日期，顯示用 |
| `summary` | 否 | 列表上的一句話摘要 |
| `source` | 否 | 原始課程連結，會顯示在文章最後 |
| `draft` | 否 | 設成 `true` 就不會發布 |

## 怎麼新增一個系列

1. 在 `content/` 開一個新資料夾，例如 `content/project-management/`
2. 在 `site.json` 的 `series` 陣列加一筆：

```json
{
  "slug": "project-management",
  "title": "專案管理筆記",
  "description": "系列說明",
  "categories": ["基礎", "進階"]
}
```

## 本機預覽

```bash
pip install markdown
python3 build.py
cd dist && python3 -m http.server 8000
```

然後開 http://localhost:8000

## 部署

推上 `main` 分支後，GitHub Actions 會自動建置並部署，約一到兩分鐘後生效。
不需要手動做任何事。

## 檔案結構

```
content/        筆記原始檔（Markdown）
site.json       網站標題、系列定義
build.py        建置腳本
static/         CSS 等靜態檔案
dist/           建置產物（不進版控）
```
