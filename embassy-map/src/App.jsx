import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import { Icon } from 'leaflet'
import { FiAlertCircle, FiCheckCircle, FiShield, FiGlobe, FiMap } from 'react-icons/fi'
import axios from 'axios'
import 'leaflet/dist/leaflet.css'
import './App.css'

const CORS_PROXIES = [
  "https://api.allorigins.win/raw?url=",
  "https://corsproxy.io/?",
  "https://cors-anywhere.herokuapp.com/",
  "https://api.codetabs.com/v1/proxy?quest="
];

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

const fetchWithRetry = async (url, maxRetries = 3) => {
  let lastError = null;

  for (let i = 0; i < maxRetries; i++) {
    try {
      // D'abord essayer sans proxy
      try {
        const response = await axios.get(url, {
          timeout: 5000,
          headers: {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (compatible; EmbassyMap/1.0)'
          }
        });
        return response;
      } catch (directError) {
        console.log(`Tentative directe échouée pour ${url}, utilisation du proxy...`);
      }

      // Si échec, essayer avec un proxy
      const proxy = CORS_PROXIES[i % CORS_PROXIES.length];
      const proxyUrl = `${proxy}${encodeURIComponent(url)}`;
      console.log(`Tentative avec proxy ${proxyUrl}`);

      const response = await axios.get(proxyUrl, {
        timeout: 5000,
        headers: {
          'Accept': 'application/json, text/plain, */*',
          'User-Agent': 'Mozilla/5.0 (compatible; EmbassyMap/1.0)'
        }
      });

      return response;
    } catch (error) {
      lastError = error;
      console.error(`Tentative ${i + 1}/${maxRetries} échouée pour ${url}:`, error.message);

      if (i === maxRetries - 1) {
        throw new Error(`Échec après ${maxRetries} tentatives. Dernière erreur: ${error.message}`);
      }

      await delay(1000 * Math.pow(2, i));
    }
  }

  throw lastError;
};

const calculateCyberScore = (embassy, rssData) => {
  let score = 50; // Score de base

  // Facteurs positifs
  if (embassy.websiteStatus?.code === 200) score += 10;
  if (rssData && !rssData.error) score += 15;
  if (rssData?.pubDate) {
    const pubDate = new Date(rssData.pubDate);
    const now = new Date();
    const daysDiff = (now - pubDate) / (1000 * 60 * 60 * 24);
    if (daysDiff < 7) score += 10; // Article récent
  }

  // Facteurs négatifs
  if (embassy.websiteStatus?.code !== 200) score -= 20;
  if (rssData?.error) score -= 15;
  if (!rssData?.description) score -= 5;

  // Limiter le score entre 0 et 100
  return Math.max(0, Math.min(100, score));
};

const getScoreColor = (score) => {
  if (score >= 80) return '#4CAF50'; // Vert
  if (score >= 60) return '#FFC107'; // Jaune
  if (score >= 40) return '#FF9800'; // Orange
  return '#F44336'; // Rouge
};

const getScoreDescription = (score) => {
  if (score >= 90) return "Excellente cybersécurité - Pays très bien protégé";
  if (score >= 80) return "Bonne cybersécurité - Protection efficace";
  if (score >= 70) return "Cybersécurité moyenne - Protection correcte";
  if (score >= 60) return "Cybersécurité faible - Besoin d'amélioration";
  return "Cybersécurité très faible - Risque important";
};

const EmbassyList = () => {
  const [embassies, setEmbassies] = useState([]);
  const [rssData, setRssData] = useState({});
  const [cyberScores, setCyberScores] = useState({});
  const [loading, setLoading] = useState(true);

  // Fonction pour extraire le nom du pays entre parenthèses
  const extractCountryName = (embassyName) => {
    // Gestion des cas spéciaux avec "au Canada" et "en Australie"
    if (embassyName.includes("au Canada")) return "Canada";
    if (embassyName.includes("en Australie")) return "Australia";
    if (embassyName.includes("à Téhéran")) return "Iran";
    if (embassyName.includes("à Kuala Lumpur")) return "Malaysia";
    if (embassyName.includes("à Rabat")) return "Morocco";
    if (embassyName.includes("à Alger")) return "Algeria";
    if (embassyName.includes("en Italie")) return "Italy";
    if (embassyName.includes("en Arabie Saoudite")) return "Saudi Arabia";
    if (embassyName.includes("en Égypte")) return "Egypt";
    if (embassyName.includes("en Chine")) return "China";
    if (embassyName.includes("en Corée du Sud")) return "South Korea";
    if (embassyName.includes("en Inde")) return "India";
    if (embassyName.includes("en France")) return "France";

    // Pour les autres cas, chercher le nom entre parenthèses
    const match = embassyName.match(/\((.*?)\)/);
    if (match) {
      const countryName = match[1];
      // Mapping des noms de pays
      const countryMapping = {
        'États-Unis': 'United States',
        'Allemagne': 'Germany',
        'Royaume-Uni': 'United Kingdom',
        'Japon': 'Japan',
        'Russie': 'Russia',
        'Brésil': 'Brazil',
        'Espagne': 'Spain',
        'Maroc': 'Morocco',
        'Algérie': 'Algeria',
        'Italie': 'Italy',
        'Arabie Saoudite': 'Saudi Arabia',
        'Égypte': 'Egypt',
        'Chine': 'China',
        'Corée du Sud': 'South Korea',
        'Inde': 'India',
        'Canada': 'Canada',
        'Australie': 'Australia',
        'Iran': 'Iran',
        'Malaisie': 'Malaysia',
        'Thaïlande': 'Thailand',
        'Vietnam': 'Vietnam',
        'France': 'France'
      };
      return countryMapping[countryName] || countryName;
    }
    return embassyName;
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Récupérer les données des ambassades
        const embassyResponse = await fetchWithRetry('https://rococo-florentine-06d544.netlify.app/embassies.json');
        console.log("Données des ambassades récupérées :", embassyResponse.data);

        // Récupérer les scores de cybersécurité
        const cyberScoresResponse = await fetchWithRetry('/cyber_scores.json');
        console.log("Scores de cybersécurité récupérés :", cyberScoresResponse.data);
        setCyberScores(cyberScoresResponse.data);

        // Récupérer les données RSS depuis le fichier local
        const rssResponse = await fetchWithRetry('/rss_feeds.json');
        console.log("Données RSS brutes :", rssResponse.data);
        console.log("Clés disponibles dans les données RSS :", Object.keys(rssResponse.data));

        // Vérifier si les données sont bien un objet
        if (typeof rssResponse.data === 'object' && rssResponse.data !== null) {
          console.log("Format des données RSS valide, mise à jour de l'état...");
          setRssData(rssResponse.data);
        } else {
          console.error("Format de données RSS invalide :", rssResponse.data);
        }

        const embassiesWithStatus = await Promise.all(embassyResponse.data.map(async (embassy) => {
          try {
            const siteResponse = await fetchWithRetry(embassy["Site internet"]);
            embassy.websiteStatus = {
              code: siteResponse.status,
              status: "En ligne",
              lastChecked: new Date().toISOString()
            };
          } catch (error) {
            embassy.websiteStatus = {
              code: 404,
              status: "Hors ligne",
              lastChecked: new Date().toISOString(),
              error: error.message
            };
          }
          return embassy;
        }));

        setEmbassies(embassiesWithStatus);
      } catch (error) {
        console.error("Erreur lors de la récupération des données :", error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  // Ajouter un useEffect pour surveiller les changements de rssData
  useEffect(() => {
    console.log("État rssData mis à jour :", rssData);
  }, [rssData]);

  if (loading) {
    return <div className="loading">Chargement...</div>;
  }

  return (
    <div className="app-container">
      <div className="embassy-list">
        <h1>
          <FiMap className="icon" />
          Ambassades de France
        </h1>
        {embassies.length === 0 ? (
          <p>Aucune ambassade à afficher.</p>
        ) : (
          embassies.map((embassy) => {
            const countryName = extractCountryName(embassy.Nom);
            const countryRssData = rssData[countryName];
            const cyberScore = cyberScores[countryName] || 0;
            console.log(`Traitement des données RSS pour ${embassy.Nom}:`, {
              countryName,
              hasData: !!countryRssData,
              hasError: countryRssData?.error,
              title: countryRssData?.title,
              description: countryRssData?.description
            });

            return (
              <div key={embassy.Nom} className="embassy-item">
                <div className="embassy-header">
                  <h3>{embassy.Nom}</h3>
                </div>

                <div className="embassy-status">
                  <p className={embassy.websiteStatus?.code === 200 ? 'status-success' : 'status-danger'}>
                    {embassy.websiteStatus?.code === 200 ? <FiCheckCircle /> : <FiAlertCircle />}
                    Site internet : <a href={embassy["Site internet"]}>{embassy["Site internet"]}</a>
                  </p>
                </div>

                <div className="country-cyber-score">
                  <h4>
                    Score ITU Global Cybersecurity Index
                  </h4>
                  <div className="score-container">
                    <span className="score-value">{cyberScore.toFixed(2).replace('.', ',')}</span>
                  </div>
                  <p className="score-description">{getScoreDescription(cyberScore)}</p>
                </div>

                {countryRssData && !countryRssData.error && countryRssData.title ? (
                  <div className="rss-feed">
                    <h4><FiGlobe /> Dernière actualité</h4>
                    <p className="rss-title">{countryRssData.title}</p>
                    {countryRssData.pubDate && (
                      <p className="rss-date">Publié le : {new Date(countryRssData.pubDate).toLocaleDateString('fr-FR')}</p>
                    )}
                    <div className="rss-links">
                      {countryRssData.link && (
                        <a href={countryRssData.link} target="_blank" rel="noopener noreferrer" className="rss-link">
                          <FiGlobe className="icon" /> Lire l'article complet
                        </a>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="rss-feed">
                    <h4><FiGlobe /> Flux RSS</h4>
                    <p className="rss-error">
                      {countryRssData?.error || "Aucune actualité disponible pour le moment"}
                    </p>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      <div className="map-container">
        <MapContainer
          center={[48.8566, 2.3522]}
          zoom={2}
          scrollWheelZoom={false}
          style={{
            height: '100%',
            width: '100%',
            borderRadius: '12px',
            overflow: 'hidden'
          }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            className="map-tiles"
          />
          {embassies.map((embassy) => {
            const countryName = extractCountryName(embassy.Nom);
            const countryRssData = rssData[countryName];
            const cyberScore = cyberScores[countryName] || 0;

            return (
              <Marker
                key={embassy.Nom}
                position={[embassy.Latitude, embassy.Longitude]}
                icon={new Icon({
                  iconUrl: embassy.websiteStatus?.code === 200 ? '/marker-icon-green.png' : '/marker-icon-red.png',
                  iconSize: [25, 41],
                  iconAnchor: [12, 41]
                })}>
                <Popup>
                  <div className="popup-content">
                    <h3>{embassy.Nom}</h3>
                    <p>Statut site : {embassy.websiteStatus?.status}</p>
                    {countryRssData && !countryRssData.error && (
                      <div className="popup-rss">
                        <p><strong>Dernière actualité :</strong></p>
                        <p>{countryRssData.title}</p>
                        <p className="rss-date">{new Date(countryRssData.pubDate).toLocaleDateString()}</p>
                      </div>
                    )}
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
};

export default EmbassyList;