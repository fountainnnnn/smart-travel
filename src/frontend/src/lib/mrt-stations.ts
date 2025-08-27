// Canonical names for MRT & LRT stations by code.
// Covers: NSL, EWL (+CG branch), DTL, CCL (+CE ext), NEL, TEL,
// and LRT lines BPL, SLRT (SE/SW), PLRT (PE/PW).

export const MRT_STATION_NAMES: Record<string, string> = {
  // ----------------------
  // North South Line (NSL)
  // ----------------------
  NS1: "Jurong East",
  NS2: "Bukit Batok",
  NS3: "Bukit Gombak",
  NS4: "Choa Chu Kang",
  NS5: "Yew Tee",
  // NS6 reserved (future Sungei Kadut)
  NS7: "Kranji",
  NS8: "Marsiling",
  NS9: "Woodlands",
  NS10: "Admiralty",
  NS11: "Sembawang",
  NS12: "Canberra",
  NS13: "Yishun",
  NS14: "Khatib",
  NS15: "Yio Chu Kang",
  NS16: "Ang Mo Kio",
  NS17: "Bishan",
  NS18: "Braddell",
  NS19: "Toa Payoh",
  NS20: "Novena",
  NS21: "Newton",
  NS22: "Orchard",
  NS23: "Somerset",
  NS24: "Dhoby Ghaut",
  NS25: "City Hall",
  NS26: "Raffles Place",
  NS27: "Marina Bay",
  NS28: "Marina South Pier",

  // ---------------------
  // East West Line (EWL)
  // ---------------------
  EW1: "Pasir Ris",
  EW2: "Tampines",
  EW3: "Simei",
  EW4: "Tanah Merah",
  EW5: "Bedok",
  EW6: "Kembangan",
  EW7: "Eunos",
  EW8: "Paya Lebar",
  EW9: "Aljunied",
  EW10: "Kallang",
  EW11: "Lavender",
  EW12: "Bugis",
  EW13: "City Hall",
  EW14: "Raffles Place",
  EW15: "Tanjong Pagar",
  EW16: "Outram Park",
  EW17: "Tiong Bahru",
  EW18: "Redhill",
  EW19: "Queenstown",
  EW20: "Commonwealth",
  EW21: "Buona Vista",
  EW22: "Dover",
  EW23: "Clementi",
  EW24: "Jurong East",
  EW25: "Chinese Garden",
  EW26: "Lakeside",
  EW27: "Boon Lay",
  EW28: "Pioneer",
  EW29: "Joo Koon",
  EW30: "Gul Circle",
  EW31: "Tuas Crescent",
  EW32: "Tuas West Road",
  EW33: "Tuas Link",

  // Changi Airport Branch (CGL) – codes share with EWL
  CG1: "Expo",
  CG2: "Changi Airport",

  // ----------------------
  // Downtown Line (DTL)
  // ----------------------
  DT1: "Bukit Panjang",
  DT2: "Cashew",
  DT3: "Hillview",
  DT4: "Hume", // opened 2023
  DT5: "Beauty World",
  DT6: "King Albert Park",
  DT7: "Sixth Avenue",
  DT8: "Tan Kah Kee",
  DT9: "Botanic Gardens",
  DT10: "Stevens",
  DT11: "Newton",
  DT12: "Little India",
  DT13: "Rochor",
  DT14: "Bugis",
  DT15: "Promenade",
  DT16: "Bayfront",
  DT17: "Downtown",
  DT18: "Telok Ayer",
  DT19: "Chinatown",
  DT20: "Fort Canning",
  DT21: "Bencoolen",
  DT22: "Jalan Besar",
  DT23: "Bendemeer",
  DT24: "Geylang Bahru",
  DT25: "Mattar",
  DT26: "MacPherson",
  DT27: "Ubi",
  DT28: "Kaki Bukit",
  DT29: "Bedok North",
  DT30: "Bedok Reservoir",
  DT31: "Tampines West",
  DT32: "Tampines",
  DT33: "Tampines East",
  DT34: "Upper Changi",
  DT35: "Expo",
  // Future DTL3e (planned)
  DT36: "Xilin",
  DT37: "Sungei Bedok",

  // ---------------------
  // Circle Line (CCL/CEL)
  // ---------------------
  CC1: "Dhoby Ghaut",
  CC2: "Bras Basah",
  CC3: "Esplanade",
  CC4: "Promenade",
  CC5: "Nicoll Highway",
  CC6: "Stadium",
  CC7: "Mountbatten",
  CC8: "Dakota",
  CC9: "Paya Lebar",
  CC10: "MacPherson",
  CC11: "Tai Seng",
  CC12: "Bartley",
  CC13: "Serangoon",
  CC14: "Lorong Chuan",
  CC15: "Bishan",
  CC16: "Marymount",
  CC17: "Caldecott",
  CC18: "Bukit Brown (Not in Service)", // non-operational
  CC19: "Botanic Gardens",
  CC20: "Farrer Road",
  CC21: "Holland Village",
  CC22: "Buona Vista",
  CC23: "one-north",
  CC24: "Kent Ridge",
  CC25: "Haw Par Villa",
  CC26: "Pasir Panjang",
  CC27: "Labrador Park",
  CC28: "Telok Blangah",
  CC29: "HarbourFront",

  // Circle Line Extension (CEL)
  CE1: "Bayfront",
  CE2: "Marina Bay",

  // ----------------------
  // North East Line (NEL)
  // ----------------------
  NE1: "HarbourFront",
  // NE2 intentionally unused
  NE3: "Outram Park",
  NE4: "Chinatown",
  NE5: "Clarke Quay",
  NE6: "Dhoby Ghaut",
  NE7: "Little India",
  NE8: "Farrer Park",
  NE9: "Boon Keng",
  NE10: "Potong Pasir",
  NE11: "Woodleigh",
  NE12: "Serangoon",
  NE13: "Kovan",
  NE14: "Hougang",
  NE15: "Buangkok",
  NE16: "Sengkang",
  NE17: "Punggol",

  // ------------------------------
  // Thomson–East Coast Line (TEL)
  // ------------------------------
  TE1: "Woodlands North",
  TE2: "Woodlands",
  TE3: "Woodlands South",
  TE4: "Springleaf",
  TE5: "Lentor",
  TE6: "Mayflower",
  TE7: "Bright Hill",
  TE8: "Upper Thomson",
  TE9: "Caldecott",
  TE10: "Mount Pleasant", // unopened (shell)
  TE11: "Orchard Boulevard",
  TE12: "Orchard",
  TE13: "Great World",
  TE14: "Havelock",
  TE15: "Outram Park",
  TE16: "Maxwell",
  TE17: "Shenton Way",
  TE18: "Marina Bay",
  TE19: "Gardens by the Bay",
  TE20: "Marina South", // unopened
  TE21: "Founders' Memorial", // future
  TE22: "Tanjong Rhu",
  TE23: "Katong Park",
  TE24: "Tanjong Katong",
  TE25: "Marine Parade",
  TE26: "Marine Terrace",
  TE27: "Siglap",
  TE28: "Bayshore",
  TE29: "—", // (reserved; if your feed ever surfaces it, update)
  TE30: "Bedok South", // future
  TE31: "Sungei Bedok", // future TEL terminus & DTL interchange

  // --------------------------
  // Bukit Panjang LRT (BPLRT)
  // --------------------------
  BP1: "Choa Chu Kang",
  BP2: "South View",
  BP3: "Keat Hong",
  BP4: "Teck Whye",
  BP5: "Phoenix",
  BP6: "Bukit Panjang",
  BP7: "Petir",
  BP8: "Pending",
  BP9: "Bangkit",
  BP10: "Fajar",
  BP11: "Segar",
  BP12: "Jelapang",
  BP13: "Senja",
  // BP14 Ten Mile Junction (Closed Permanently)

  // ------------------------
  // Sengkang LRT (SKLRT/SLRT)
  // ------------------------
  SE1: "Rumbia",
  SE2: "Bakau",
  SE3: "Kangkar",
  SE4: "Ranggung",
  SW1: "Cheng Lim",
  SW2: "Farmway",
  SW3: "Kupang",
  SW4: "Thanggam",
  SW5: "Fernvale",
  SW6: "Layar",
  SW7: "Tongkang",
  SW8: "Renjong",

  // -----------------------
  // Punggol LRT (PGLRT/PLRT)
  // -----------------------
  PE1: "Cove",
  PE2: "Meridian",
  PE3: "Coral Edge",
  PE4: "Riviera",
  PE5: "Kadaloor",
  PE6: "Oasis",
  PE7: "Damai",
  PW1: "Sam Kee",
  PW2: "Teck Lee", // (unopened)
  PW3: "Punggol Point",
  PW4: "Samudera",
  PW5: "Nibong",
  PW6: "Sumang",
  PW7: "Soo Teck",
};

// Label helper – prefers code, then fallback, then "Unknown".
export function labelStation(code?: string | null, fallback?: string | null) {
  if (code && MRT_STATION_NAMES[code]) return MRT_STATION_NAMES[code];
  if (fallback && MRT_STATION_NAMES[fallback]) return MRT_STATION_NAMES[fallback];
  return fallback ?? code ?? "Unknown";
}

// Optional: full line names for headings
export const LINE_FULL_NAME: Record<string, string> = {
  NSL: "North South Line",
  EWL: "East West Line",
  DTL: "Downtown Line",
  CCL: "Circle Line",
  TEL: "Thomson–East Coast Line",
  NEL: "North East Line",
  BPL: "Bukit Panjang LRT",
  SLRT: "Sengkang LRT",
  PLRT: "Punggol LRT",
  CGL: "Changi Airport Branch",
  CEL: "Circle Line Extension",
};
