// Offline camera list for the Command view (js/command-map.js).
//
// Extracted verbatim from the NYC DOT / NYCTMC public camera API
// (https://webcams.nyctmc.org/api/cameras) on 2026-10-30: 60 cameras,
// 12 per borough, every entry online ("isOnline":"true") at extraction
// time. Field values are copied exactly from the API output — names,
// coordinates, and ids are never invented or rounded. At runtime the
// app tries the live API first (through the app server's same-origin
// proxy, then directly); this subset ships so the map, list,
// and pins still work offline, and the UI says "offline camera list"
// whenever this fallback is the source.
//
// These are public NYC DOT traffic cameras used as TEST feeds for the
// assessment pipeline. Nothing here is this app's own camera, and
// being in this list implies no monitoring: the app only ever samples
// a camera after an operator adds it to the watch list.

export const CAMERA_API_URL = "https://webcams.nyctmc.org/api/cameras";

// Same-origin proxy for the list above, served by the app server
// (GET /api/cameras, server/cameras.mjs): the NYCTMC API sends no
// Access-Control-Allow-Origin header, so browsers cannot fetch it
// directly. The app tries this proxy first, then the direct URL,
// then FALLBACK_CAMERAS below.
export const CAMERA_PROXY_URL = "/api/cameras";

export const FALLBACK_CAMERAS = [
  // ---- Manhattan (12) ----
  { id: "330e2a88-3cea-4ce5-b1a2-ae8440de9b1a", name: "1 Ave @ 84 St", latitude: 40.7755, longitude: -73.9502, area: "Manhattan", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/330e2a88-3cea-4ce5-b1a2-ae8440de9b1a/image" },
  { id: "4f8c2e84-c15a-4474-91fb-7e14554d4c4e", name: "Central Park West @ 65 St", latitude: 40.771797, longitude: -73.979217, area: "Manhattan", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/4f8c2e84-c15a-4474-91fb-7e14554d4c4e/image" },
  { id: "984ebbad-ca64-41d8-8008-63aaae316952", name: "Central Park West @ 72 St", latitude: 40.776225, longitude: -73.975974, area: "Manhattan", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/984ebbad-ca64-41d8-8008-63aaae316952/image" },
  { id: "8a6bc417-4877-4ebe-8052-88c1b261baf1", name: "Central Park West @ 86 St", latitude: 40.785302, longitude: -73.969353, area: "Manhattan", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/8a6bc417-4877-4ebe-8052-88c1b261baf1/image" },
  { id: "ec1e7b42-18de-4475-8c89-9e80f21e5b6c", name: "FDR Drive @ 122 St", latitude: 40.798685, longitude: -73.929148, area: "Manhattan", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/ec1e7b42-18de-4475-8c89-9e80f21e5b6c/image" },
  { id: "053e8995-f8cb-4d02-a659-70ac7c7da5db", name: "Broadway @ 45 St", latitude: 40.757953, longitude: -73.98549, area: "Manhattan", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/053e8995-f8cb-4d02-a659-70ac7c7da5db/image" },
  { id: "332f161d-47cb-4c8a-b6b6-5ad48a55c978", name: "Ave of Americas @ Central Park South", latitude: 40.765683, longitude: -73.976229, area: "Manhattan", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/332f161d-47cb-4c8a-b6b6-5ad48a55c978/image" },
  { id: "8cc75cbc-e050-4947-aee8-639f63fe4ca7", name: "Canal Street @ Chrystie Street", latitude: 40.715821, longitude: -73.994913, area: "Manhattan", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/8cc75cbc-e050-4947-aee8-639f63fe4ca7/image" },
  { id: "09b1235e-d2d1-4451-83a5-5a1c3ec280aa", name: "St Nicholas Ave @ 145 St", latitude: 40.824031, longitude: -73.94477, area: "Manhattan", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/09b1235e-d2d1-4451-83a5-5a1c3ec280aa/image" },
  { id: "b1d5d592-9e36-478e-bedc-5fb02d836bc3", name: "Sutton Pl @ 58 St", latitude: 40.758044, longitude: -73.960189, area: "Manhattan", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/b1d5d592-9e36-478e-bedc-5fb02d836bc3/image" },
  { id: "ec9ffb62-e3bf-4352-8bcf-7c9adf5fbe9c", name: "8th Ave @ 31st St", latitude: 40.750297, longitude: -73.99483, area: "Manhattan", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/ec9ffb62-e3bf-4352-8bcf-7c9adf5fbe9c/image" },
  { id: "a6bd09c7-9195-4e0b-ac0f-78114a7d63a1", name: "Park Ave @ E 125 St", latitude: 40.805313, longitude: -73.93924, area: "Manhattan", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/a6bd09c7-9195-4e0b-ac0f-78114a7d63a1/image" },
  // ---- Brooklyn (12) ----
  { id: "0039e6bf-5244-4b4e-b7dc-d02056bbfdc9", name: "Atlantic Ave @ 111 St", latitude: 40.692157, longitude: -73.834927, area: "Brooklyn", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/0039e6bf-5244-4b4e-b7dc-d02056bbfdc9/image" },
  { id: "f134b133-75ef-40a8-8fbb-f9c51355e6b5", name: "Old Fulton St @ Vine St/Hicks St - quad - 156.24", latitude: 40.701936, longitude: -73.992574, area: "Brooklyn", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/f134b133-75ef-40a8-8fbb-f9c51355e6b5/image" },
  { id: "0472fa7a-acd7-4510-a9e7-61307d4057cd", name: "Bay Pkwy @ 78 St (Kings Hwy)", latitude: 40.60632, longitude: -73.989087, area: "Brooklyn", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/0472fa7a-acd7-4510-a9e7-61307d4057cd/image" },
  { id: "8d2b3ae9-da68-4d37-8ae2-d3bc014f827b", name: "WBB - 2 NOR @ ABOVE BEDFORD AVE & S 5 St", latitude: 40.710892, longitude: -73.96362, area: "Brooklyn", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/8d2b3ae9-da68-4d37-8ae2-d3bc014f827b/image" },
  { id: "068461e2-c62f-4ce4-adac-5f9efe92af1d", name: "Bushwick Ave @ De Kalb Ave", latitude: 40.695092, longitude: -73.928357, area: "Brooklyn", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/068461e2-c62f-4ce4-adac-5f9efe92af1d/image" },
  { id: "9bdd7740-762f-48e9-b40c-3db03c2a43f5", name: "Belt Pkwy @ Ocean Pkwy", latitude: 40.583257, longitude: -73.966656, area: "Brooklyn", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/9bdd7740-762f-48e9-b40c-3db03c2a43f5/image" },
  { id: "84a2c36a-ef84-41b6-a4eb-3c3a2bf3bf10", name: "Stillwell Ave @ Surf Ave", latitude: 40.575565, longitude: -73.981202, area: "Brooklyn", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/84a2c36a-ef84-41b6-a4eb-3c3a2bf3bf10/image" },
  { id: "07c5a9ab-38b0-4176-a932-395cded5858e", name: "Cadman Plz West @ Tillary St", latitude: 40.696267, longitude: -73.991073, area: "Brooklyn", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/07c5a9ab-38b0-4176-a932-395cded5858e/image" },
  { id: "3576217a-82e8-4f2a-854f-3de97ef37362", name: "BQE @ Pearl St", latitude: 40.701273, longitude: -73.987712, area: "Brooklyn", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/3576217a-82e8-4f2a-854f-3de97ef37362/image" },
  { id: "b18d0e36-c053-435d-921e-813ab5f65a0a", name: "C2-BQE-22-WB_at_Lee_Ave-Ex31", latitude: 40.705248, longitude: -73.959172, area: "Brooklyn", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/b18d0e36-c053-435d-921e-813ab5f65a0a/image" },
  { id: "0bbea8bd-10f1-4126-b3c5-9e9432eab749", name: "Atlantic Ave @ Pennsylvania Ave", latitude: 40.675787, longitude: -73.896898, area: "Brooklyn", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/0bbea8bd-10f1-4126-b3c5-9e9432eab749/image" },
  { id: "b5d8fe4f-1cf5-4cd8-8211-8353e68da1cb", name: "Atlantic Ave @ Vanderbilt Ave", latitude: 40.6809634749315, longitude: -73.9670419692993, area: "Brooklyn", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/b5d8fe4f-1cf5-4cd8-8211-8353e68da1cb/image" },
  // ---- Queens (12) ----
  { id: "1b3248f9-f26e-4f36-943f-b7a7731595fb", name: "QBB @ Crescent St", latitude: 40.750889, longitude: -73.940613, area: "Queens", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/1b3248f9-f26e-4f36-943f-b7a7731595fb/image" },
  { id: "1e88b34b-2058-402e-9a3d-aca1c57696bf", name: "GCP @ 31 ST", latitude: 40.770109, longitude: -73.917131, area: "Queens", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/1e88b34b-2058-402e-9a3d-aca1c57696bf/image" },
  { id: "300e0508-3c7e-4ac5-8527-b75bcf8292b8", name: "Hillside Ave @ Little Neck Pkwy", latitude: 40.736207, longitude: -73.713777, area: "Queens", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/300e0508-3c7e-4ac5-8527-b75bcf8292b8/image" },
  { id: "0bb2c096-0377-41f7-a451-56944aa8dae2", name: "Belt Pkwy @ 125 St", latitude: 40.665007, longitude: -73.819358, area: "Queens", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/0bb2c096-0377-41f7-a451-56944aa8dae2/image" },
  { id: "9fa5b0dd-e955-449e-97e1-9c53ad9c23a8", name: "GCP @ LGA 94 St Exit", latitude: 40.771466, longitude: -73.877462, area: "Queens", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/9fa5b0dd-e955-449e-97e1-9c53ad9c23a8/image" },
  { id: "a01a8c98-d314-4eb4-b97c-4a4f80d71c4b", name: "Seagirt Blvd @ B 32 St", latitude: 40.5958, longitude: -73.764771, area: "Queens", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/a01a8c98-d314-4eb4-b97c-4a4f80d71c4b/image" },
  { id: "ae1960ee-1f34-4774-88f5-b195b9c2a505", name: "C5-LIE-15-WB_at_Queens_Blvd-Ex19", latitude: 40.732725, longitude: -73.8692, area: "Queens", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/ae1960ee-1f34-4774-88f5-b195b9c2a505/image" },
  { id: "67f77766-bd19-4082-adeb-88d59866c490", name: "Long Island Expy @ QMT @ Pulaski Br", latitude: 40.74148, longitude: -73.9509, area: "Queens", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/67f77766-bd19-4082-adeb-88d59866c490/image" },
  { id: "8e07d72b-94cd-44c4-b92a-48decda031d2", name: "Queens Blvd @ 39 St - East", latitude: 40.74383, longitude: -73.926217, area: "Queens", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/8e07d72b-94cd-44c4-b92a-48decda031d2/image" },
  { id: "16d86749-6ec5-4594-8ccc-56c9507fedc3", name: "Rockaway Blvd @ S. Conduit Ave", latitude: 40.6668, longitude: -73.779833, area: "Queens", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/16d86749-6ec5-4594-8ccc-56c9507fedc3/image" },
  { id: "279720e5-7db3-4143-9608-531cfc50dc25", name: "College Point Blvd @ 35 Ave", latitude: 40.763583, longitude: -73.836038, area: "Queens", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/279720e5-7db3-4143-9608-531cfc50dc25/image" },
  { id: "8ccc0c64-65a5-42f9-9eba-cf7aa4a51b09", name: "Belt Pkwy @ Cross Island Split", latitude: 40.682884, longitude: -73.726459, area: "Queens", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/8ccc0c64-65a5-42f9-9eba-cf7aa4a51b09/image" },
  // ---- Bronx (12) ----
  { id: "09afb231-ef10-470f-bf54-0f44fc2dc18f", name: "Pelham Shore Rd @ City Island Rd", latitude: 40.864552, longitude: -73.813781, area: "Bronx", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/09afb231-ef10-470f-bf54-0f44fc2dc18f/image" },
  { id: "b221fdc4-ca81-41ae-875e-bf0341377758", name: "C1-BRE-06_W - WB_at_CBX-Hutch_Int-EX6A", latitude: 40.829767, longitude: -73.834824, area: "Bronx", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/b221fdc4-ca81-41ae-875e-bf0341377758/image" },
  { id: "2f28f8df-5eb5-4327-ab1f-7feaf2630b34", name: "Grand Concourse @ Bedford Park Blvd", latitude: 40.872207, longitude: -73.887658, area: "Bronx", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/2f28f8df-5eb5-4327-ab1f-7feaf2630b34/image" },
  { id: "4284c61f-eb9c-419d-99e4-48a7ef681e62", name: "PELHAM PKWY @ WILLIAMSBRIDGE RD", latitude: 40.856997, longitude: -73.856265, area: "Bronx", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/4284c61f-eb9c-419d-99e4-48a7ef681e62/image" },
  { id: "073df904-1699-4b0d-b779-d3a95305e4fd", name: "C1-BRE-08-NB_at_Waterbury_Ave-Ex7B", latitude: 40.838087, longitude: -73.824953, area: "Bronx", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/073df904-1699-4b0d-b779-d3a95305e4fd/image" },
  { id: "bfeb2434-fd55-4024-8172-f9602ea6ae06", name: "Hutchhinson River Pkwy @ Waterbury Ave", latitude: 40.83536, longitude: -73.83849, area: "Bronx", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/bfeb2434-fd55-4024-8172-f9602ea6ae06/image" },
  { id: "09cc9eed-0732-4199-a6ca-b3d0bbbad860", name: "C1-MDE-06-NB_at_Macombs_Dam_Br-Ex5", latitude: 40.828221, longitude: -73.930969, area: "Bronx", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/09cc9eed-0732-4199-a6ca-b3d0bbbad860/image" },
  { id: "b19c9130-3a2d-4f7a-94a5-495eeea219ef", name: "C1-BRE-11-SB_at_Buhre_Ave-Ex8A", latitude: 40.84897, longitude: -73.827533, area: "Bronx", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/b19c9130-3a2d-4f7a-94a5-495eeea219ef/image" },
  { id: "f1acca9b-0030-49c5-b589-33ab6ac24657", name: "C1-TNE-01-SB_at_Otis-Ave", latitude: 40.835488, longitude: -73.824394, area: "Bronx", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/f1acca9b-0030-49c5-b589-33ab6ac24657/image" },
  { id: "6a841f4c-93ef-4f51-b38d-80e70053ff8d", name: "WEBSTER AVE @ NEREID AVE", latitude: 40.9011, longitude: -73.8616, area: "Bronx", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/6a841f4c-93ef-4f51-b38d-80e70053ff8d/image" },
  { id: "351d3d12-fd9e-4e4c-b279-cd8f3f1f194c", name: "C1-MDE-01-Cntr_at_E.135th_St-Ex1", latitude: 40.803545, longitude: -73.916135, area: "Bronx", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/351d3d12-fd9e-4e4c-b279-cd8f3f1f194c/image" },
  { id: "572b1058-c33a-4de2-8f35-0f3e9e92bc33", name: "CBX @ Morris Ave & 174th ST", latitude: 40.844785, longitude: -73.909282, area: "Bronx", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/572b1058-c33a-4de2-8f35-0f3e9e92bc33/image" },
  // ---- Staten Island (12) ----
  { id: "0f5e11ff-0ecc-4622-a32e-bb80a6b2c1c6", name: "Hylan Blvd @ Arden Ave", latitude: 40.529434, longitude: -74.161351, area: "Staten Island", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/0f5e11ff-0ecc-4622-a32e-bb80a6b2c1c6/image" },
  { id: "2d1ed99a-c3d3-4616-a0d6-a9fe16f3e48c", name: "SIE @ Clove Rd", latitude: 40.610941, longitude: -74.098029, area: "Staten Island", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/2d1ed99a-c3d3-4616-a0d6-a9fe16f3e48c/image" },
  { id: "07f88e60-2b93-4bba-9784-8cac3c9b7f52", name: "C3-SIE-02-EB_at_WSE_Int-Ex3", latitude: 40.622323, longitude: -74.174917, area: "Staten Island", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/07f88e60-2b93-4bba-9784-8cac3c9b7f52/image" },
  { id: "0ff541bf-1be1-4bbf-88c5-3a570541e7d2", name: "Father Capodanno Blvd @ Sands LN", latitude: 40.590366, longitude: -74.066659, area: "Staten Island", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/0ff541bf-1be1-4bbf-88c5-3a570541e7d2/image" },
  { id: "c941aa1a-ebde-4589-9669-eaf67279dfab", name: "Drumgoole Rd W @ Arden Ave - quad - ptz - 141.10", latitude: 40.54696, longitude: -74.18117, area: "Staten Island", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/c941aa1a-ebde-4589-9669-eaf67279dfab/image" },
  { id: "171d87f4-033f-4769-ae00-7819baa8034e", name: "SIE @ Fingerboard Rd", latitude: 40.603841, longitude: -74.069281, area: "Staten Island", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/171d87f4-033f-4769-ae00-7819baa8034e/image" },
  { id: "8df73045-61fd-4394-b21a-dfa3f440d6e7", name: "C3-MLK-01-SB_at_Watchogue_Rd-Ex10", latitude: 40.618503, longitude: -74.151462, area: "Staten Island", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/8df73045-61fd-4394-b21a-dfa3f440d6e7/image" },
  { id: "1c3a5c25-a40c-40d6-8f6b-030294269fd1", name: "Lily Pond Ave @ School Rd", latitude: 40.604846, longitude: -74.065641, area: "Staten Island", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/1c3a5c25-a40c-40d6-8f6b-030294269fd1/image" },
  { id: "6cc9b754-096d-4c5c-94b7-64f6b69523d5", name: "C3-WSE-12-NB_at_Bloomfield_Ave_Ex9", latitude: 40.612239, longitude: -74.180319, area: "Staten Island", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/6cc9b754-096d-4c5c-94b7-64f6b69523d5/image" },
  { id: "02ac2943-68f1-478d-b8d5-148a97e77e27", name: "C3-KWV-01-NB_at_Tyrllan_Ave-Outrbr", latitude: 40.525433, longitude: -74.230189, area: "Staten Island", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/02ac2943-68f1-478d-b8d5-148a97e77e27/image" },
  { id: "1389ca99-0d3f-4c27-bc45-b0aa238ea7d2", name: "SIE @ Richmond Ave", latitude: 40.614885, longitude: -74.157435, area: "Staten Island", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/1389ca99-0d3f-4c27-bc45-b0aa238ea7d2/image" },
  { id: "5920b7ab-9e05-429f-971a-b235f3ea8dd9", name: "Amboy Rd @ Nelson Ave", latitude: 40.549932, longitude: -74.150849, area: "Staten Island", isOnline: "true", imageUrl: "https://webcams.nyctmc.org/api/cameras/5920b7ab-9e05-429f-971a-b235f3ea8dd9/image" },
];

// Guaranteed-live camera WALL feeds: the three Caltrans District 7
// (Los Angeles) CCTV snapshots verified end-to-end on 2026-10-30 (see
// trio-live-feed-verification-2026-10-30.md: fetched twice, bytes
// differed, Access-Control-Allow-Origin: *). They are NOT New York
// cameras and are never plotted on the NYC map; the wall labels them
// Los Angeles, Caltrans, test feeds.
export const WALL_FEEDS = [
  { id: "caltrans-i5-slauson", name: "I-5 @ Slauson Ave", area: "Los Angeles — Caltrans (test feed)", imageUrl: "https://cwwp2.dot.ca.gov/data/d7/cctv/image/i52slausonave/i52slausonave.jpg" },
  { id: "caltrans-i5-i10", name: "I-5, south of I-10", area: "Los Angeles — Caltrans (test feed)", imageUrl: "https://cwwp2.dot.ca.gov/data/d7/cctv/image/i517southofi10/i517southofi10.jpg" },
  { id: "caltrans-i110-ave26", name: "I-110 @ Avenue 26 Off Ramp", area: "Los Angeles — Caltrans (test feed)", imageUrl: "https://cwwp2.dot.ca.gov/data/d7/cctv/image/i110196avenue26offramp/i110196avenue26offramp.jpg" },
];
