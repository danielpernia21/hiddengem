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
    ("WMI", "Podlasie",                      5, [5,6,9,10],         "Bialowieza primeval forest, bison, Tatar villages"),
    ("BUD", "Bukk / Villany",                4, [5,6,9,10],         "Cave baths and cellar-row wine villages"),
    ("VNO", "Aukstaitija",                   5, [6,7,8,9],          "Lake district, wooden villages, almost no international visitors"),
    ("RIX", "Kurzeme / Latgale",             5, [6,7,8,9],          "Baltic dune coast or the lake belt on the Russian border"),
]

# ---------------------------------------------------------------------------
# PENDING — Ryanair's BCN network, rows you haven't scored yet.
#
# quiet=0 means main.py skips them (MIN_QUIET=3). They are inert until YOU
# fill in the score and the reason. The region names below are candidates,
# not research — check each one on a map before trusting it.
#
# Rule for the `why`: something that is true in a specific month and that
# you could verify. Not "charming villages". If you can't write one, the
# row doesn't belong here — delete it.
#
# Hubs left out on purpose (IBZ, PMI, MAH, DUB, MLA, PRG, VIE, BER, MXP,
# STN/LTN, BRU, ARN, CPH): the airport IS the destination for most people,
# so the satellite trick works badly. Add them back only if you find a real one.
# ---------------------------------------------------------------------------

PENDING = [
    ("AHO", "Planargia / Bosa, Sardinia",      0, [], ""),
    ("BLQ", "Appennino Bolognese",             0, [], ""),
    ("PEG", "Valnerina / Monti Sibillini",     0, [], ""),
    ("REG", "Aspromonte",                      0, [], ""),
    ("TRN", "Val Maira / Valli Occitane",      0, [], ""),
    ("BGY", "Val Brembana / Val Seriana",      0, [], ""),
    ("VCE", "Val Belluna / Colli Euganei",     0, [], ""),
    ("ZAD", "Velebit / inland Lika",           0, [], ""),
    ("BTS", "Small Carpathians / Zahorie",     0, [], ""),
    ("POZ", "Wielkopolska lake belt",          0, [], ""),
    ("GDN", "Kashubia / Vistula Spit",         0, [], ""),
    ("CFU", "inland Corfu / Diapontia",        0, [], ""),
    ("TLL", "Soomaa / Lahemaa",                0, [], ""),
    ("LUX", "Eislek / Mullerthal",             0, [], ""),
    ("CRL", "Ardennes / Gaume",                0, [], ""),
    ("BVA", "Vexin / Picardy",                 0, [], ""),
    ("CGN", "Eifel",                           0, [], ""),
    ("HHN", "Hunsruck",                        0, [], ""),
    ("ORK", "West Cork / Beara",               0, [], ""),
    ("EDI", "Angus Glens",                     0, [], ""),
    ("PIK", "Galloway Forest",                 0, [], ""),
    ("NCL", "Cheviots / Northumberland",       0, [], ""),
    ("EMA", "Charnwood / Peak fringe",         0, [], ""),
    ("LPL", "Clwydian Range",                  0, [], ""),
    ("BHX", "Welsh Marches / Shropshire",      0, [], ""),
    ("BRS", "Forest of Dean / Exmoor",         0, [], ""),
    ("MAN", "Forest of Bowland",               0, [], ""),
    ("FEZ", "Middle Atlas / Sefrou",           0, [], ""),
    ("RAK", "High Atlas valleys",              0, [], ""),
    ("TNG", "Talassemtane / Rif",              0, [], ""),
    ("NDR", "Beni Snassen",                    0, [], ""),
    ("OUD", "Beni Snassen / Zegzel",           0, [], ""),
    ("RBA", "Zerhoun / Moulay Idriss",         0, [], ""),
    ("OZZ", "Draa valley",                     0, [], ""),
]

# Promote a row by moving it into REGIONS with a real score and reason.
REGIONS = REGIONS + [r for r in PENDING if r[2] >= 3]