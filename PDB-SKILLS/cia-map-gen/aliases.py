"""Historical / colloquial place-name aliases and named regions.

Maps common names not present in Natural Earth (or historical names from the
declassified era) to modern equivalents or to preset bounding boxes.
"""

# Single-word or phrase -> canonical modern country name
COUNTRY_ALIASES = {
    "rhodesia": "zimbabwe",
    "zaire": "democratic republic of the congo",
    "burma": "myanmar",
    "siam": "thailand",
    "ceylon": "sri lanka",
    "persia": "iran",
    "formosa": "taiwan",
    "upper volta": "burkina faso",
    "ussr": "russia",
    "soviet union": "russia",
    "czechoslovakia": "czech republic",
    "east germany": "germany",
    "west germany": "germany",
    "yugoslavia": "serbia",
    "cape verde": "cabo verde",
    "ivory coast": "cote d'ivoire",
    "the united states": "united states of america",
    "usa": "united states of america",
    "us": "united states of america",
    "uk": "united kingdom",
    "uae": "united arab emirates",
}

# Named regions -> (list of focus countries, optional explicit bbox override)
# bbox format: (min_lon, min_lat, max_lon, max_lat); None means auto-compute from focus countries.
NAMED_REGIONS = {
    "middle east": (
        ["Saudi Arabia", "Iran", "Iraq", "Syria", "Jordan", "Israel",
         "Lebanon", "Yemen", "Oman", "United Arab Emirates", "Qatar",
         "Kuwait", "Bahrain", "Egypt", "Turkey"],
        None,
    ),
    "horn of africa": (
        ["Ethiopia", "Somalia", "Eritrea", "Djibouti", "Kenya", "Sudan",
         "South Sudan"],
        None,
    ),
    "southeast asia": (
        ["Thailand", "Vietnam", "Cambodia", "Laos", "Myanmar", "Malaysia",
         "Singapore", "Indonesia", "Philippines", "Brunei"],
        None,
    ),
    "central america": (
        ["Guatemala", "Belize", "Honduras", "El Salvador", "Nicaragua",
         "Costa Rica", "Panama"],
        None,
    ),
    "scandinavia": (
        ["Norway", "Sweden", "Finland", "Denmark", "Iceland"],
        None,
    ),
    "balkans": (
        ["Serbia", "Croatia", "Bosnia and Herzegovina", "Slovenia",
         "Montenegro", "Kosovo", "North Macedonia", "Albania", "Bulgaria",
         "Romania", "Greece"],
        None,
    ),
    "southern africa": (
        ["South Africa", "Namibia", "Botswana", "Zimbabwe", "Mozambique",
         "Zambia", "Malawi", "Lesotho", "Eswatini", "Angola"],
        None,
    ),
    "maghreb": (
        ["Morocco", "Algeria", "Tunisia", "Libya", "Mauritania"],
        None,
    ),
    "caucasus": (
        ["Georgia", "Armenia", "Azerbaijan", "Turkey", "Russia", "Iran"],
        (38, 38, 52, 47),
    ),
    "indochina": (
        ["Vietnam", "Cambodia", "Laos", "Thailand", "Myanmar"],
        None,
    ),
}
