import feedparser
import json
import os

# Anime News Network RSS Feed
RSS_URL = "https://www.animenewsnetwork.com/all/rss.xml"

def fetch_news():
    print("Fetching latest anime news from Anime News Network...")
    feed = feedparser.parse(RSS_URL)
    
    articles = []
    # Grab up to the latest 10 articles
    for entry in feed.entries[:10]:
        # Shorten and clean up summary if needed
        summary = entry.get("summary", "Read the full update on Anime News Network.")
        # Strip simple HTML tags if present in RSS summary
        if "<" in summary and ">" in summary:
            import re
            summary = re.sub('<[^<]+?>', '', summary)
        
        # Keep it short as requested
        if len(summary) > 180:
            summary = summary[:177] + "..."

        articles.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.get("published", "Recent"),
            "summary": summary
        })
        
    return articles

def update_html(articles):
    html_path = "index.html"
    if not os.path.exists(html_path):
        print("index.html not found!")
        return

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Generate the news cards HTML
    cards_html = ""
    for art in articles:
        cards_html += f"""
        <div class="news-card">
            <div class="news-meta">{art['published']}</div>
            <a href="{art['link']}" target="_blank" class="news-title">{art['title']}</a>
            <p class="news-summary">{art['summary']}</p>
        </div>
        """

    # Replace the placeholder or old feed in index.html
    # We look for the main element tag content
    marker_start = '<main id="news-feed">'
    marker_end = '</main>'
    
    start_idx = content.find(marker_start)
    end_idx = content.find(marker_end)
    
    if start_idx != -1 and end_idx != -1:
        new_content = (
            content[:start_idx + len(marker_start)] +
            "\n" + cards_html + "\n        " +
            content[end_idx:]
        )
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Successfully updated index.html with latest news!")
    else:
        print("Could not find news feed container in HTML.")

if __name__ == "__main__":
    news = fetch_news()
    if news:
        update_html(news)
