# ⚡ Blinkit Scout — Inventory Intelligence

> Search Blinkit from a browser. Enter a keyword + PIN code and get the top 10 products with **name, price, delivery time, listing type (Ad/Organic), and available inventory count** — exported as JSON or CSV.

---

## 🏗️ Architecture

```
┌─────────────────────────┐        ┌──────────────────────────────┐
│  Frontend (Vercel)      │  POST  │  Backend (Railway)           │
│  index.html             │ ─────► │  FastAPI + Selenium          │
│  Static HTML/CSS/JS     │        │  Runs headless Chrome        │
│  yourapp.vercel.app     │ ◄───── │  Scrapes Blinkit live        │
└─────────────────────────┘  JSON  └──────────────────────────────┘
```

**Why two parts?** Browsers can't scrape other websites due to CORS security. The backend runs Chrome on a server and returns the data as JSON.

---

## 📁 Project Structure

```
blinkit-scraper/
├── index.html          ← Frontend (deploy to Vercel)
├── vercel.json         ← Vercel config
├── api/
│   ├── main.py         ← FastAPI app
│   ├── scraper.py      ← Selenium scraping logic
│   └── requirements.txt
├── Procfile            ← Railway start command
├── railway.json        ← Railway config
├── nixpacks.toml       ← Installs Chrome on Railway
└── .gitignore
```

---

## 🚀 Deployment

### STEP 1 — Deploy Backend on Railway (free tier available)

Railway will run the FastAPI + Selenium server with Chrome.

1. Go to **[railway.app](https://railway.app)** → Sign in with GitHub
2. Click **"New Project" → "Deploy from GitHub repo"**
3. Select this repo → Railway auto-detects `nixpacks.toml`
4. Click **Deploy**
5. Once live, go to **Settings → Networking → Generate Domain**
6. Copy your URL: `https://blinkit-scraper-production.up.railway.app`

### STEP 2 — Update Frontend with Backend URL

1. Open `index.html`
2. Find this line near the top of the `<script>`:
   ```js
   : 'https://YOUR_BACKEND_URL_HERE';
   ```
3. Replace with your Railway URL:
   ```js
   : 'https://blinkit-scraper-production.up.railway.app';
   ```
4. Commit the change

### STEP 3 — Deploy Frontend on Vercel

1. Go to **[vercel.com](https://vercel.com)** → Import this GitHub repo
2. Vercel reads `vercel.json` and serves `index.html`
3. Your dashboard is live at `yourapp.vercel.app`

---

## 💻 Run Locally

```bash
# Install Python deps
pip install -r api/requirements.txt

# Start backend
uvicorn api.main:app --reload --port 8000

# Open frontend
open index.html
# (or just double-click index.html in your file browser)
```

The frontend auto-detects `localhost` and points to `http://localhost:8000`.

---

## 📋 API Reference

### `POST /scrape`

**Request:**
```json
{
  "keyword": "bread",
  "pincode": "110001"
}
```

**Response:**
```json
{
  "keyword": "bread",
  "pincode": "110001",
  "total": 8,
  "products": [
    {
      "Rank": 1,
      "Product Name": "Britannia Bread White",
      "Unit Quantity": "400 g",
      "Selling Price": "₹45",
      "Delivery Time": "10 mins",
      "Listing Type": "Organic",
      "Available Inventory": 12
    }
  ]
}
```

### `GET /health`
Returns `{"status": "healthy"}`

---

## ⚠️ Notes

- Each scrape takes **2–5 minutes** because the inventory check clicks + repeatedly per product
- Railway free tier sleeps after 30 min inactivity — first request after sleep takes ~30s to wake up
- Blinkit's HTML classes may change; if scraping breaks, update the XPath selectors in `api/scraper.py`
