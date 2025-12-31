/**
 * Shared constants for the frontend application
 * These should match the backend constants for consistency
 */

// Position mapping for better display
export const POSITION_MAPPING: Record<string, string> = {
  "GK": "Goalkeeper",
  "DF": "Defender",
  "MF": "Midfielder",
  "FW": "Forward",
  "DF,MF": "Defender/Midfielder",
  "MF,DF": "Defender/Midfielder",
  "FW,MF": "Winger",
  "MF,FW": "Winger",
  "DF,FW": "Wing-Back",
  "Unknown": "Unknown",
};

// Position colors for consistent styling across the application
export const POSITION_COLORS: Record<string, string> = {
  "GK": "#FF6B35",      // Orange for goalkeepers
  "DF": "#2563EB",      // Blue for defenders
  "MF": "#00E673",      // Green (accent) for midfielders
  "FW": "#DC2626",      // Red for forwards
  "DF,MF": "#06B6D4",   // Cyan for defender/midfielders
  "MF,DF": "#06B6D4",   // Cyan for midfielder/defenders
  "FW,MF": "#8B5CF6",   // Purple for forward/midfielders (wingers)
  "MF,FW": "#8B5CF6",   // Purple for midfielder/forwards (wingers)
  "DF,FW": "#F59E0B",   // Amber for defender/forwards (wing-backs)
  "Unknown": "#9CA3AF", // Gray for unknown positions
};

// Position emojis for visual representation
export const POSITION_EMOJIS: Record<string, string> = {
  "GK": "🥅",
  "DF": "🛡️",
  "MF": "⚡",
  "FW": "⚽",
  "DF,MF": "🔄",
  "MF,DF": "🔄",
  "FW,MF": "🌟",
  "MF,FW": "🌟",
  "DF,FW": "🚀",
  "Unknown": "👤",
};

/**
 * Get the color for a given position
 */
export function getPositionColor(position: string | null | undefined): string {
  if (!position) return POSITION_COLORS["Unknown"];
  return POSITION_COLORS[position] || POSITION_COLORS["Unknown"];
}

/**
 * Get the emoji for a given position
 */
export function getPositionEmoji(position: string | null | undefined): string {
  if (!position) return POSITION_EMOJIS["Unknown"];
  return POSITION_EMOJIS[position] || POSITION_EMOJIS["Unknown"];
}

/**
 * Get the display name for a given position
 */
export function getPositionDisplayName(position: string | null | undefined): string {
  if (!position) return POSITION_MAPPING["Unknown"];
  return POSITION_MAPPING[position] || position;
}

/**
 * Get position from a position string, handling multi-position cases
 */
export function getPlayerPosition(position: string | null | undefined): string {
  if (!position) return "Unknown";
  // Handle multi-position players (e.g., "FW,MF")
  if (position.includes(",")) return position;
  return position;
}

// Country code to full name mapping (ISO 3166-1 alpha-3 and FIFA codes)
export const COUNTRY_NAMES: Record<string, string> = {
  "AFG": "Afghanistan",
  "ALB": "Albania",
  "ALG": "Algeria",
  "AND": "Andorra",
  "ANG": "Angola",
  "ARG": "Argentina",
  "ARM": "Armenia",
  "AUS": "Australia",
  "AUT": "Austria",
  "AZE": "Azerbaijan",
  "BAN": "Bangladesh",
  "BDI": "Burundi",
  "BEL": "Belgium",
  "BEN": "Benin",
  "BFA": "Burkina Faso",
  "BFR": "Burkina Faso",
  "BIH": "Bosnia and Herzegovina",
  "BLR": "Belarus",
  "BOL": "Bolivia",
  "BOT": "Botswana",
  "BRA": "Brazil",
  "BUL": "Bulgaria",
  "CAN": "Canada",
  "CGO": "Congo",
  "CHA": "Chad",
  "CHI": "Chile",
  "CHN": "China",
  "CIV": "Côte d'Ivoire",
  "CMR": "Cameroon",
  "COD": "DR Congo",
  "COL": "Colombia",
  "COM": "Comoros",
  "CPV": "Cape Verde",
  "CRC": "Costa Rica",
  "CRO": "Croatia",
  "CTA": "Central African Republic",
  "CUB": "Cuba",
  "CUW": "Curaçao",
  "CYP": "Cyprus",
  "CZE": "Czech Republic",
  "DEN": "Denmark",
  "DJI": "Djibouti",
  "DOM": "Dominican Republic",
  "ECU": "Ecuador",
  "EGY": "Egypt",
  "ENG": "England",
  "EQG": "Equatorial Guinea",
  "ERI": "Eritrea",
  "ESP": "Spain",
  "EST": "Estonia",
  "ETH": "Ethiopia",
  "FIN": "Finland",
  "FRA": "France",
  "FRO": "Faroe Islands",
  "GAB": "Gabon",
  "GAM": "Gambia",
  "GEO": "Georgia",
  "GER": "Germany",
  "GHA": "Ghana",
  "GIB": "Gibraltar",
  "GLP": "Guadeloupe",
  "GRN": "Grenada",
  "GNB": "Guinea-Bissau",
  "GRE": "Greece",
  "GUA": "Guatemala",
  "GUF": "French Guiana",
  "GUI": "Guinea",
  "HAI": "Haiti",
  "HON": "Honduras",
  "HUN": "Hungary",
  "IDN": "Indonesia",
  "IND": "India",
  "IRE": "Republic of Ireland",
  "IRL": "Republic of Ireland",
  "IRN": "Iran",
  "IRQ": "Iraq",
  "ISL": "Iceland",
  "ISR": "Israel",
  "ITA": "Italy",
  "JAM": "Jamaica",
  "JOR": "Jordan",
  "JPN": "Japan",
  "KAZ": "Kazakhstan",
  "KEN": "Kenya",
  "KOR": "South Korea",
  "KSA": "Saudi Arabia",
  "KUW": "Kuwait",
  "KVX": "Kosovo",
  "LAT": "Latvia",
  "LBY": "Libya",
  "LIB": "Lebanon",
  "LBR": "Liberia",
  "LIE": "Liechtenstein",
  "LTU": "Lithuania",
  "LUX": "Luxembourg",
  "LVA": "Latvia",
  "MAD": "Madagascar",
  "MAR": "Morocco",
  "MAS": "Malaysia",
  "MDA": "Moldova",
  "MEX": "Mexico",
  "MKD": "North Macedonia",
  "MLI": "Mali",
  "MLT": "Malta",
  "MNE": "Montenegro",
  "MOZ": "Mozambique",
  "MRT": "Mauritania",
  "MTN": "Mauritania",
  "MTQ": "Martinique",
  "MWI": "Malawi",
  "NED": "Netherlands",
  "NGA": "Nigeria",
  "NIC": "Nicaragua",
  "NIG": "Niger",
  "NIR": "Northern Ireland",
  "NOR": "Norway",
  "NZL": "New Zealand",
  "OMA": "Oman",
  "PAK": "Pakistan",
  "PAN": "Panama",
  "PAR": "Paraguay",
  "PER": "Peru",
  "PHI": "Philippines",
  "PLE": "Palestine",
  "POL": "Poland",
  "POR": "Portugal",
  "PRK": "North Korea",
  "QAT": "Qatar",
  "ROU": "Romania",
  "RSA": "South Africa",
  "RUS": "Russia",
  "RWA": "Rwanda",
  "SAL": "El Salvador",
  "SCO": "Scotland",
  "SEN": "Senegal",
  "SLE": "Sierra Leone",
  "SMA": "San Marino",
  "SRB": "Serbia",
  "SSD": "South Sudan",
  "SUR": "Suriname",
  "STP": "São Tomé and Príncipe",
  "SUD": "Sudan",
  "SVK": "Slovakia",
  "SVN": "Slovenia",
  "SUI": "Switzerland",
  "SWE": "Sweden",
  "SYR": "Syria",
  "TAN": "Tanzania",
  "THA": "Thailand",
  "TJK": "Tajikistan",
  "TOG": "Togo",
  "TRI": "Trinidad and Tobago",
  "TUN": "Tunisia",
  "TUR": "Turkey",
  "UAE": "United Arab Emirates",
  "UGA": "Uganda",
  "UKR": "Ukraine",
  "URU": "Uruguay",
  "USA": "United States",
  "UZB": "Uzbekistan",
  "VEN": "Venezuela",
  "VIE": "Vietnam",
  "WAL": "Wales",
  "YEM": "Yemen",
  "ZAM": "Zambia",
  "ZIM": "Zimbabwe",
};

/**
 * Get the full country name from a 3-letter code
 */
export function getCountryName(code: string | null | undefined): string {
  if (!code) return "Unknown";
  return COUNTRY_NAMES[code.toUpperCase()] || code;
}

// Default filter values used across the application
export const DEFAULT_FILTERS = {
  league: "Aggregated (All Leagues)",
  season: "2526",
  team: "All Teams",
  nation: "All Nations",
  position: "All Positions",
  minMinutes: "0",
};
