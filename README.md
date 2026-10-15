# Thread — Fashion Recommendation Studio + AI Stylist

A responsive fashion recommendation website built with HTML, CSS, and vanilla JavaScript, a Python local server, and an SQLite3 database. The optional AI Stylist uses the OpenAI API when configured.

## Quick start (Windows)
1. Extract the ZIP to a folder.
2. Install Python 3 if it isn't installed.
3. Double-click `start_windows.bat`.
4. Optionally paste your OpenAI API key to enable conversational AI. Leave it blank to use the built-in local style matcher.
5. Open **http://127.0.0.1:8000** in your browser.

## Quick start (Mac / Linux)
1. Extract the ZIP and open a terminal in the folder.
2. Run `chmod +x start_mac_linux.sh` if needed, then `./start_mac_linux.sh`.
3. Optionally enter your OpenAI API key when prompted.
4. Open **http://127.0.0.1:8000** in your browser.

## SQLite3 database
The server automatically creates `thread_ai.db` in the project folder the first time it runs. SQLite3 is included with most standard Python installations, so no separate database server or package installation is normally needed.

The database contains:
- `products` — the 40 sample catalogue items; seeded from `products_seed.json` on first run.
- `favourites` — saved product IDs, persisted between visits when the site is opened through the local server.
- `style_profile` — the latest style quiz preferences (vibe, palette, and occasion).

The website loads its catalogue from `/api/products`. Saved items and the style quiz profile synchronize with `/api/saved` and `/api/profile`. The database is local to this project folder. If you delete `thread_ai.db`, the server recreates it and reseeds the sample products on the next launch.

## Enable full AI chat
Create an API key in your OpenAI account and provide it when the start script asks, or set the `OPENAI_API_KEY` environment variable before launching `python app_server.py`. The key is used only by the local Python server and is not placed in website JavaScript. You need API access and may incur API usage charges. You can set a different model with `OPENAI_MODEL` (default: `gpt-4o-mini`).

If you leave the key blank, the AI Stylist panel still works with local catalogue-based outfit suggestions; full conversational AI replies are not available in that mode.

## Features
- 40 sample fashion items across tops, bottoms, dresses, outerwear, shoes, and accessories
- SQLite3-backed product catalogue, saved favourites, and style profile
- AI Stylist chat panel with quick prompts, chat history, style profile and saved-item context
- Optional OpenAI-powered recommendations with product matches from the local catalogue
- Local style-matching fallback when no API key is configured
- Website-native product details popup, product descriptions, sample INR prices/ratings and size selector
- Search, category, budget, style-vibe filters and sorting
- Favorites drawer, style quiz, personalized recommendation strip and copyable shortlist
- Responsive desktop/mobile layout and keyboard shortcuts

## Notes
This is a front-end demo, not a live store. Prices, ratings, and availability are samples. Newsletter entries are stored only in the browser and are not sent to a server. Product photos and fonts use Unsplash/Google Fonts and require internet access. Do not share your API key or commit it into source control.


### Product image mapping

Each catalog product has a distinct Unsplash image ID in both `products_seed.json` and the SQLite `products.img` column. The same mapping is also present in the front-end fallback catalogue in `app.js`. If a remote image is unavailable, the UI displays a category-specific placeholder instead of reusing the same unrelated stock photo. Product images are loaded from Unsplash, so an internet connection is needed to view them.
