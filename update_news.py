import feedparser
import json
import os
import re

# Anime News Network RSS Feed
RSS_URL = "https://www.animenewsnetwork.com/all/rss.xml"

def extract_image(entry):
    image_url = ""
    
    # Check enclosure or media content tags first
    if 'enclosures' in entry and len(entry.enclosures) > 0:
        for enc in entry.enclosures:
            if 'image' in enc.get('type', ''):
                return enc.get('href', '')
                
    if 'media_content' in entry and len(entry.media_content) > 0:
        image_url = entry.media_content[0].get('url', '')
        if image_url:
            return image_url
            
    if 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
        image_url = entry.media_thumbnail[0].get('url', '')
        if image_url:
            return image_url

    # Check content or summary HTML string for an <img> tag
    raw_html = ""
    if 'content' in entry and len(entry.content) > 0:
        raw_html = entry.content[0].get('value', '')
    elif 'summary' in entry:
        raw_html = entry.summary
        
    if raw_html:
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_html)
        if img_match:
            image_url = img_match.group(1)
            
    return image_url

def fetch_news():
    print("Fetching latest anime news and images from Anime News Network...")
    feed = feedparser.parse(RSS_URL)
    
    articles = []
    for entry in feed.entries[:10]:
        summary = entry.get("summary", "Read the full update on Anime News Network.")
        
        # Strip HTML tags from summary text for clean display
        if "<" in summary and ">" in summary:
            summary = re.sub('<[^<]+?>', '', summary)
        
        if len(summary) > 160:
            summary = summary[:157] + "..."

        image_url = extract_image(entry)

        articles.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.get("published", "Recent"),
            "summary": summary,
            "image": image_url
        })
        
    return articles

def update_html(articles):
    html_path = "index.html"
    if not os.path.exists(html_path):
        print("index.html not found!")
        return

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    cards_html = ""
    for art in articles:
        # Only add the image block if an image URL was successfully extracted
        img_tag = f'<div class="news-img-container"><img src="{art["image"]}" alt="Article thumbnail" loading="lazy"></div>' if art['image'] else ''
        
        cards_html += f"""
        <div class="news-card">
            {img_tag}
            <div class="news-content-box">
                <div class="news-meta">{art['published']}</div>
                <a href="{art['link']}" target="_blank" class="news-title">{art['title']}</a>
                <p class="news-summary">{art['summary']}</p>
            </div>
        </div>
        """

    marker_start = '<main id="news-feed" class="news-grid">'
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
        print("Successfully updated index.html with images!")
    else:
        print("Could not find news feed container in HTML.")

if __name__ == "__main__":
    news = fetch_news()
    if news:
        update_html(news)
