"""
The editorial core. Do NOT generate this with an LLM.

quiet:  your own 1-5 rating. 5 = you'd be surprised to hear another Spanish voice.
        Anything you scored 1-2 is a hub, not a gem. Filtered out at runtime.
months: months the region is actually worth visiting (1-12).
why:    one concrete reason, not a vibe. Used verbatim in the message.

Add rows over time. When you run out of rows you can honestly score 4+,
that is the supply problem showing up, and it is a real finding.
"""

REGIONS = [
    # code, region, quiet, months, why
    ("VGO", "Ribeira Sacra, Ourense",        5, [4,5,6,9,10],       "Canyon vineyards worked by rope; Roman thermal pools free in Ourense"),
    ("SCQ", "Costa da Morte",                4, [5,6,7,8,9],        "Empty Atlantic beaches an hour from the Camino crowds"),
    ("OVD", "Somiedo, Asturias",             5, [5,6,9,10],         "Brown bear valleys, teito shepherd huts, zero tour buses"),
    ("BIO", "Valles Pasiegos",               4, [5,6,9,10],         "Green Cantabrian valleys behind the Bilbao day-trip radius"),
    ("SVQ", "Sierra de Aracena",             4, [3,4,5,10,11],      "Chestnut forests and Iberian ham villages, 90 min from Seville"),
    ("AGP", "Sierra de las Nieves",          3, [4,5,6,10,11],      "Newest Spanish national park, still unbadged"),
    ("MAD", "Sierra de Ayllon",              4, [5,6,10,11],        "Black-slate villages, beech forest turning in November"),

    ("OPO", "Douro Superior",                4, [4,5,6,9,10],       "Upstream past the tour boats; harvest in late September"),
    ("LIS", "Beira Baixa",                   5, [3,4,5,10],         "Schist villages and Tejo gorges, almost no foreign visitors"),
    ("FAO", "Alentejo Litoral",              4, [4,5,6,9,10],       "Cliff coast north of the Algarve line, storks nesting on sea stacks"),

    ("TLS", "Aveyron / Aubrac",              4, [5,6,9,10],         "Plateau villages, Laguiole knives, transhumance in late May"),
    ("LYS", "Ardeche / Vercors",             3, [5,6,9,10],         "Gorges without the Verdon crowds; caves and limestone plateaus"),
    ("MRS", "Vallee de l'Ubaye",             4, [6,7,9,10],         "High alpine valleys the Cote d'Azur traffic never reaches"),
    ("BOD", "Landes interior",               4, [5,6,9,10],         "Pine forest, thermal towns, Adour valley food"),

    ("PSA", "Lunigiana / Garfagnana",        4, [5,6,9,10],         "Castle valleys between Tuscany and Liguria, no Chianti pricing"),
    ("FCO", "Tuscia, Alto Lazio",            4, [4,5,10,11],        "Etruscan tombs and tufa towns; Civita without the Rome day-trip"),
    ("NAP", "Cilento",                       4, [5,6,9,10],         "Greek temples, empty coast, the original Mediterranean diet"),
    ("BRI", "Alta Murgia / Gargano",         4, [4,5,6,10],         "Karst plateau and Umbra forest, inland from the Puglia rush"),
    ("CTA", "Nebrodi / Val di Noto interior",4, [4,5,10,11],        "Beech forest above the sea; baroque towns with no coach parks"),
    ("PMO", "Madonie",                       4, [4,5,6,10],         "Mountain villages an hour from Palermo, manna ash harvest"),
    ("CAG", "Ogliastra / Sarrabus",          5, [5,6,9,10],         "Supramonte gorges and beaches you walk to"),
    ("TRS", "Inland Istria / Carso",         4, [4,5,6,9,10],       "Truffle hills and karst caves, 40 min from the airport"),

    ("TIA", "Permet / Vjosa valley",         5, [5,6,9,10],         "Last wild river in Europe, thermal springs, near-zero tourism"),
    ("SJJ", "Herzegovina backcountry",       5, [4,5,6,9,10],       "Karst plateaus and river canyons behind Mostar"),
    ("ZAG", "Zagorje / Lika",                4, [5,6,9,10],         "Hill castles and Plitvice's quiet neighbours"),
    ("SKG", "Zagori / Pelion",               4, [5,6,9,10],         "Stone arch bridges, Vikos gorge, mountain villages"),
    ("ATH", "Mani / Arcadia",                4, [4,5,6,9,10],       "Tower houses and empty Peloponnese mountain roads"),
    ("SOF", "Rhodopes",                      5, [5,6,9,10],         "Bagpipe villages, gorges, bear country"),
    ("OTP", "Fagaras / Danube Delta",        4, [5,6,7,9],          "Alpine ridge or reed labyrinth, depending on the month"),

    ("KRK", "Beskids",                       4, [5,6,9,10],         "Wooden churches and empty ridge walks south of Krakow"),
    ("WAW", "Podlasie",                      5, [5,6,9,10],         "Bialowieza primeval forest, bison, Tatar villages"),
    ("BUD", "Bukk / Villany",                4, [5,6,9,10],         "Cave baths and cellar-row wine villages"),
    ("VNO", "Aukstaitija",                   5, [6,7,8,9],          "Lake district, wooden villages, almost no international visitors"),
    ("RIX", "Kurzeme / Latgale",             5, [6,7,8,9],          "Baltic dune coast or the lake belt on the Russian border"),
]
