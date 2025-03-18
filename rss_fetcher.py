import json
import aiohttp
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional
import logging
from concurrent.futures import ThreadPoolExecutor
import re
from urllib.parse import urljoin
import os
from cyber_score import get_country_cyber_score
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rss_fetcher.log'),
        logging.StreamHandler()
    ]
)

# Définition des flux RSS par région
RSS_FEEDS = {
    # Amérique du Nord
    "United States": "https://www.cisa.gov/cybersecurity-advisories/alerts.xml",  # CISA Alerts
    "Canada": "https://www.cyber.gc.ca/api/cccs/rss/v1/get?feed=alerts_advisories&lang=fr",  # Canadian Centre for Cyber Security

    # Europe
    "Germany": "https://www.heise.de/security/feed.xml",  # Heise Security
    "United Kingdom": "https://www.theregister.co.uk/security/headlines.rss",  # The Register Security
    "Italy": "https://www.cybersecurity360.it/feed/",  # Cybersecurity 360
    "Spain": "https://www.computerworld.es/feed/",  # Computerworld España Seguridad
    "France": "https://www.cert.ssi.gouv.fr/feed/",  # CERT.gouv.fr Security Alerts

    # Asie
    "Japan": "https://rss.itmedia.co.jp/rss/2.0/itmedia_all.xml",  # ITmedia Security
    "Russia": "https://habr.com/ru/rss/all/",  # Habr Security
    "South Korea": "https://zdnet.co.kr/feed",  # ZDNet Korea Security
    "India": "https://cyberops.in/blog/feed/",  # Cybersecurity India
    "Thailand": "https://www.thaicert.or.th/sitemap.rss",  # ThaiCERT
    "Vietnam": "https://www.vncert.gov.vn/feed/",  # VNCERT/CC Security Alerts
    "China": "https://www.csa.gov.sg/Content/RSS-Feed",  # CNCERT/CC Security Alerts
    "Malaysia": "https://www.mycert.org.my/feed/",  # MyCERT Security Alerts

    # Moyen-Orient et Afrique
    "Egypt": "https://egcert.eg/feed/",  # EG-CERT Security Alerts
    "Saudi Arabia": "https://www.nca.gov.sa/feed/",  # Saudi National Cybersecurity Authority
    "Iran": "https://cert.ir/feed/",  # MAHER Security Center

    # Amérique du Sud
    "Brazil": "https://www.cert.br/rss/certbr-rss.xml",  # CERT.br Security Alerts

    # Afrique du Nord
    "Morocco": "https://www.marocert.ma/feed/",  # MarocCERT Security Alerts
    "Algeria": "https://www.cerist.dz/index.php/en/?format=feed&type=rss",  # CERT-DZ Security Alerts

    # Océanie
    "Australia": "	https://auscert.org.au/rss/bulletins/",  # Australian Cyber Security Centre
}

# Proxies CORS
CORS_PROXIES = [
    "https://api.allorigins.win/raw?url=",
    "https://corsproxy.io/?",
    "https://cors-anywhere.herokuapp.com/",
    "https://api.codetabs.com/v1/proxy?quest="
]

def clean_html(html_content: str) -> str:
    """Nettoie le contenu HTML pour n'en garder que le texte."""
    if not html_content:
        return ""
    # Supprime les balises HTML
    text = re.sub('<[^<]+?>', '', html_content)
    # Remplace les entités HTML
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = text.replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&apos;', "'")
    # Supprime les espaces multiples
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_link(item: ET.Element, base_url: str) -> Optional[str]:
    """Extrait le lien de l'élément en gérant différents formats."""
    # Atom avec attribut rel="alternate"
    link_elem = item.find('.//{http://www.w3.org/2005/Atom}link[@rel="alternate"]')
    if link_elem is not None and 'href' in link_elem.attrib:
        return link_elem.attrib['href']

    # RSS standard
    link_elem = item.find('link')
    if link_elem is not None and link_elem.text:
        return link_elem.text

    # Atom standard
    link_elem = item.find('{http://www.w3.org/2005/Atom}link')
    if link_elem is not None and 'href' in link_elem.attrib:
        return link_elem.attrib['href']

    # RSS avec guid
    guid_elem = item.find('guid')
    if guid_elem is not None and guid_elem.text:
        return guid_elem.text

    # Si aucun lien n'est trouvé, essayer d'extraire du contenu
    content_elem = item.find('content')
    if content_elem is not None:
        # Chercher un lien dans le contenu
        link_match = re.search(r'href=["\'](https?://[^"\']+)["\']', content_elem.text)
        if link_match:
            return link_match.group(1)

    return None

def extract_title(item: ET.Element) -> Optional[str]:
    """Extrait le titre de l'élément en gérant différents formats."""
    # Atom
    title_elem = item.find('{http://www.w3.org/2005/Atom}title')
    if title_elem is not None:
        return title_elem.text.strip()

    # RSS standard
    title_elem = item.find('title')
    if title_elem is not None:
        return title_elem.text.strip()

    return None

def extract_description(item: ET.Element) -> Optional[str]:
    """Extrait la description de l'élément en gérant différents formats."""
    # Atom
    desc_elem = item.find('{http://www.w3.org/2005/Atom}summary')
    if desc_elem is not None and desc_elem.text:
        return desc_elem.text.strip()

    # RSS standard
    desc_elem = item.find('description')
    if desc_elem is not None and desc_elem.text:
        return desc_elem.text.strip()

    # Content
    content_elem = item.find('content')
    if content_elem is not None and content_elem.text:
        return content_elem.text.strip()

    return None

def extract_date(item: ET.Element) -> Optional[str]:
    """Extrait la date de l'élément en gérant différents formats."""
    date_fields = [
        '{http://www.w3.org/2005/Atom}updated',  # Atom updated
        '{http://www.w3.org/2005/Atom}published',  # Atom published
        'pubDate',  # RSS standard
        'published',  # RSS alternatif
        'updated',  # RSS alternatif
        'date',  # RSS alternatif
        'dc:date',  # Dublin Core
        '{http://purl.org/dc/elements/1.1/}date'  # Dublin Core avec namespace
    ]
    
    for field in date_fields:
        date_elem = item.find(field)
        if date_elem is not None and date_elem.text:
            return date_elem.text.strip()
    
    return None

def parse_date(date_str: str) -> datetime:
    """Parse une date dans différents formats."""
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',  # Format RSS standard
        '%Y-%m-%dT%H:%M:%SZ',        # Format ISO 8601 (Atom)
        '%Y-%m-%dT%H:%M:%S%z',       # Format ISO 8601 avec timezone
        '%Y-%m-%d %H:%M:%S',         # Format simple
        '%Y-%m-%d'                   # Format date seule
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return datetime.now()

async def parse_rss_content(content: str, country: str, feed_url: str) -> Optional[Dict]:
    """
    Parse le contenu RSS/Atom et retourne les informations du dernier article.
    """
    try:
        # Nettoyer le contenu XML
        content = content.strip()
        if not content:
            logging.warning(f"Contenu vide pour {country}")
            return None

        # Parser le XML
        root = ET.fromstring(content)
        
        # Gestion des différents formats RSS/Atom
        items = []
        if root.tag.endswith('rss'):
            items = root.findall('.//item')
        elif root.tag.endswith('feed'):  # Atom
            items = root.findall('.//{http://www.w3.org/2005/Atom}entry')
        else:
            # Chercher des items dans n'importe quel format
            items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')

        if not items:
            logging.warning(f"Aucun article trouvé pour {country}")
            return None

        # Créer une liste de tuples (date, item) pour le tri
        items_with_dates = []
        for item in items:
            pub_date = extract_date(item)
            if pub_date:
                try:
                    date_obj = parse_date(pub_date)
                    items_with_dates.append((date_obj, item))
                except Exception as e:
                    logging.warning(f"Erreur de parsing de date pour {country}: {str(e)}")
                    continue

        # Trier par date décroissante et prendre le dernier article
        items_with_dates.sort(key=lambda x: x[0], reverse=True)
        if not items_with_dates:
            return None

        # Traiter le dernier article
        _, item = items_with_dates[0]
        
        # Extraire les informations
        title = extract_title(item)
        link = extract_link(item, feed_url)
        description = extract_description(item)
        pub_date = extract_date(item)

        # Nettoyage des données
        if description:
            description = clean_html(description)
        if title:
            title = clean_html(title)

        # Vérification des données requises
        if title or description:
            return {
                "title": title,
                "link": link,
                "description": description,
                "pubDate": pub_date,
                "lastFetched": datetime.now().isoformat(),
                "summary": "Non disponible",
                "translation": "Non disponible"
            }

        logging.warning(f"Aucun article valide trouvé pour {country}")
        return None

    except ET.ParseError as e:
        logging.error(f"Erreur de parsing XML pour {country}: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"Erreur inattendue lors du parsing pour {country}: {str(e)}")
        return None

async def fetch_with_retry(session: aiohttp.ClientSession, url: str, country: str, max_retries: int = 2) -> Optional[str]:
    """
    Récupère le contenu d'une URL avec plusieurs tentatives et proxies de manière asynchrone.
    """
    headers = {
        'Accept': 'application/xml, application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (compatible; RSSFetcher/1.0)'
    }

    for attempt in range(max_retries):
        try:
            # Tentative directe
            try:
                async with session.get(url, headers=headers, timeout=5) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logging.warning(f"Erreur HTTP {response.status} pour {country} en tentative directe")
            except Exception as e:
                logging.warning(f"Tentative directe échouée pour {country}: {str(e)}")

            # Tentative avec proxy
            proxy = CORS_PROXIES[attempt % len(CORS_PROXIES)]
            proxy_url = f"{proxy}{url}"
            logging.info(f"Tentative avec proxy {proxy_url} pour {country}")
            
            async with session.get(proxy_url, headers=headers, timeout=5) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logging.error(f"Erreur HTTP {response.status} pour {country} avec proxy {proxy}")

        except Exception as e:
            logging.error(f"Tentative {attempt + 1}/{max_retries} échouée pour {country}: {str(e)}")
            if attempt == max_retries - 1:
                logging.error(f"Échec après {max_retries} tentatives pour {country}")
                return None
            await asyncio.sleep(0.5)

    return None

async def process_feed(session: aiohttp.ClientSession, country: str, feed_url: str) -> tuple:
    """
    Traite un flux RSS individuel de manière asynchrone.
    """
    content = await fetch_with_retry(session, feed_url, country)
    if content:
        parsed_data = await parse_rss_content(content, country, feed_url)
        if parsed_data:
            # Ajouter le score de cybersécurité du pays
            cyber_score = get_country_cyber_score(country)
            if cyber_score is not None:
                parsed_data['cyberScore'] = cyber_score
            return country, parsed_data
        else:
            return country, {
                "error": "Impossible de parser le flux RSS",
                "lastFetched": datetime.now().isoformat()
            }
    else:
        return country, {
            "error": "Impossible de récupérer le flux RSS",
            "lastFetched": datetime.now().isoformat()
        }

async def process_feeds() -> Dict:
    """
    Traite tous les flux RSS en parallèle.
    """
    results = {}
    async with aiohttp.ClientSession() as session:
        # Créer des tâches pour tous les flux
        tasks = [process_feed(session, country, feed_url) 
                for country, feed_url in RSS_FEEDS.items()]
        
        # Exécuter toutes les tâches en parallèle
        completed_tasks = await asyncio.gather(*tasks)
        
        # Traiter les résultats
        for country, data in completed_tasks:
            results[country] = data
            
    return results

def clean_old_rss_files():
    """
    Supprime tous les anciens fichiers RSS en gardant uniquement le plus récent.
    """
    try:
        # Créer le dossier public s'il n'existe pas
        os.makedirs('public', exist_ok=True)
        
        # Récupérer tous les fichiers RSS
        rss_files = [f for f in os.listdir('public') if f.startswith('rss_feeds_') and f.endswith('.json')]
        logging.info(f"Fichiers RSS trouvés : {rss_files}")
        
        if len(rss_files) > 1:
            # Trier les fichiers par date (le plus récent en premier)
            rss_files.sort(reverse=True)
            latest_file = rss_files[0]
            logging.info(f"Fichier le plus récent : {latest_file}")
            
            # Supprimer tous les fichiers sauf le plus récent
            for old_file in rss_files:
                if old_file != latest_file:
                    file_path = os.path.join('public', old_file)
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            logging.info(f"Fichier supprimé avec succès : {old_file}")
                        else:
                            logging.warning(f"Le fichier n'existe pas : {old_file}")
                    except Exception as e:
                        logging.error(f"Erreur lors de la suppression du fichier {old_file}: {str(e)}")
            
            logging.info(f"Un seul fichier RSS conservé : {latest_file}")
        else:
            logging.info("Aucun ancien fichier RSS à supprimer")
            
    except Exception as e:
        logging.error(f"Erreur lors du nettoyage des fichiers RSS : {str(e)}")

async def save_cyber_scores():
    """
    Sauvegarde les scores de cybersécurité dans un fichier JSON séparé.
    """
    try:
        # Créer le dossier public s'il n'existe pas
        os.makedirs('embassy-map/public', exist_ok=True)
        
        # Récupérer tous les scores
        scores = {}
        for country in RSS_FEEDS.keys():
            score = get_country_cyber_score(country)
            if score is not None:
                scores[country] = score
        
        # Sauvegarder dans le fichier
        output_file = 'embassy-map/public/cyber_scores.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Scores de cybersécurité sauvegardés dans {output_file}")
        
    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde des scores de cybersécurité : {str(e)}")

async def main():
    """
    Fonction principale qui orchestre la récupération et le traitement des flux RSS.
    """
    try:
        # Créer le dossier public s'il n'existe pas
        os.makedirs('embassy-map/public', exist_ok=True)
        
        # Nettoyer les anciens fichiers RSS
        logging.info("Début du nettoyage des anciens fichiers RSS...")
        clean_old_rss_files()
        logging.info("Fin du nettoyage des anciens fichiers RSS")
        
        # Sauvegarder les scores de cybersécurité
        logging.info("Début de la sauvegarde des scores de cybersécurité...")
        await save_cyber_scores()
        logging.info("Fin de la sauvegarde des scores de cybersécurité")
        
        # Utiliser un nom de fichier fixe
        output_file = 'embassy-map/public/rss_feeds.json'
        
        # Traiter les flux RSS
        results = await process_feeds()
        
        # Sauvegarder les résultats
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Données sauvegardées dans {output_file}")
        
    except Exception as e:
        logging.error(f"Erreur lors de l'exécution : {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 