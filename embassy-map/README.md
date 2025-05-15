# Embassy Map 🌍

<img src="public/vite.svg" alt="Vite Logo" width="40" style="vertical-align:middle;"/> <img src="src/assets/react.svg" alt="React Logo" width="40" style="vertical-align:middle;"/>

**Embassy Map** is a web application that displays the cybersecurity status of different countries through their embassies on an interactive map, based on official RSS feeds and cybersecurity scores.

---

## Visual Overview

| High Security | Low Security |
|:--------------:|:--------------:|
| <img src="public/marker-icon-green.png" width="30"/> | <img src="public/marker-icon-red.png" width="30"/> |

- Green markers indicate good cybersecurity.
- Red markers signal high risk or unavailability.

---

## Main Features
- Interactive map of embassies with cybersecurity status.
- Automatic retrieval of cyber alerts and news by country (RSS feeds).
- Calculation and display of a cybersecurity score per country.
- Details of the latest alerts and incidents for each country.

---

## Data Examples

**Excerpt from `cyber_scores.json`:**
```json
{
  "United States": 100.0,
  "France": 95.0,
  "Germany": 98.5
}
```

**Excerpt from `rss_feeds.json`:**
```json
{
  "France": {
    "title": "Multiple vulnerabilities in IBM products (March 14, 2025)",
    "link": "https://www.cert.ssi.gouv.fr/avis/CERTFR-2025-AVI-0214/",
    "description": "Multiple vulnerabilities have been discovered in IBM products...",
    "pubDate": "Fri, 14 Mar 2025 14:02:43 +0000"
  }
}
```

---

## Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd embassy-map
   ```
2. **Install dependencies**
   ```bash
   cd embassy-map
   npm install
   ```
3. **Launch the application**
   ```bash
   npm run dev
   ```

The application will be accessible at [http://localhost:5173](http://localhost:5173)

---

## Project Structure

- `src/` : React source code
- `public/` : Static files (icons, JSON data)
- `rss_fetcher.py` : Python script to collect RSS feeds and cyber scores

---

## Credits
- Icons: [Vite](https://vitejs.dev/), [React](https://react.dev/), custom markers
- RSS Data: CERT, CISA, etc.

---

## Screenshot (to be added)
![Alt text](/embassy-map/public/EmbassyMap.png?raw=true "Embassy Map")
![Alt text](/embassy-map/public/FocusEmbassy.png?raw=true "Focus Embassy")
