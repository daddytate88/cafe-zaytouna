#!/usr/bin/env python3
"""Café Zaytouna — static multi-page site generator.

Usage:
  python3 build.py                                   # site to upload (folder: dist/), domain cafe-zaytouna.vercel.app
  python3 build.py --preview                         # self-contained preview (folder: preview/)

Edit the DATA section below (hours, phone, rating, menu, reviews), then rebuild.
"""
import base64, datetime, hashlib, html, json, os, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent
PREVIEW = "--preview" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]
SITE_URL = (args[0] if args else "https://cafe-zaytouna.vercel.app").rstrip("/")
OUT = ROOT / ("preview" if PREVIEW else "dist")
sys.path.insert(0, str(ROOT))
import legal

# =========================== DATA ===========================
NAME = "Café Zaytouna"
ORDER_URL = "https://www.ubereats.com/store-browse-uuid/d775c01b-5ecb-516e-8731-84f584defe02?diningMode=DELIVERY"
REVIEW_URL = "https://cafe-zaytouna-review.vercel.app/"
MAPS_URL = "https://maps.app.goo.gl/GZGqkZ1AyNgGVvat7"
MAP_EMBED = "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d1397.0908933942612!2d-73.6392189907404!3d45.54666850808826!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x4cc9195bad31f3e9%3A0xfad8106ace563446!2sCaf%C3%A9%20Zaytouna!5e0!3m2!1sen!2sca!4v1791501534793!5m2!1sen!2sca"
INSTAGRAM = "https://www.instagram.com/cafezaytouna/"
PHONE_E164 = "+15143835555"
PHONE = {"fr": "514 383-5555", "en": "(514) 383-5555"}
RATING, REVIEW_COUNT = 4.9, 404
GEO = (45.5466685, -73.639219)
# Monday..Sunday, 24 h clock (open, close)
HOURS = [(11, 20), (11, 20), (11, 20), (11, 20), (11, 21), (10, 21), (11, 21)]
DAYS = {"fr": ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"],
        "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}
SCHEMA_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

CATS = [
  {"id": "matchas", "fr": "Matchas", "en": "Matcha",
   "fr_d": "Du matcha latte glacé aux créations fruitées et gourmandes.",
   "en_d": "From a classic iced matcha latte to fruity and dessert-inspired creations.", "photo": "matcha-creme-brulee"},
  {"id": "lattes", "fr": "Lattes signatures", "en": "Signature lattes",
   "fr_d": "Nos lattes glacés les plus gourmands.", "en_d": "Our most indulgent iced lattes.", "photo": "latte-creme-brulee"},
  {"id": "limonades", "fr": "Limonades", "en": "Lemonades",
   "fr_d": "Pour une pause fraîche.", "en_d": "For a refreshing break.", "photo": None},
  {"id": "sandwichs", "fr": "Sandwichs", "en": "Sandwiches",
   "fr_d": "Pour accompagner votre café, à midi comme en après-midi.", "en_d": "To go with your coffee, at lunch or in the afternoon.", "photo": None},
  {"id": "cremes", "fr": "Crèmes brûlées", "en": "Crème brûlée",
   "fr_d": "La crème brûlée, à la cuillère.", "en_d": "Crème brûlée, by the spoonful.", "photo": None},
]

# Prices verified on the café's Uber Eats page (Oct 2026). Descriptions stay within what the name/photos show.
ITEMS = [
  dict(id="matcha-latte", cat="matchas", name="Matcha Latte Glacé", fr="matcha-latte-glace", en="iced-matcha-latte", price=7.95,
       fr_d="Notre matcha latte, servi sur glace.", en_d="Our matcha latte, served over ice.", en_name="Iced Matcha Latte"),
  dict(id="matcha-zaytouna", cat="matchas", name="Matcha Zaytouna Glacé", fr="matcha-zaytouna-glace", en="iced-zaytouna-matcha", price=8.70,
       fr_d="Le matcha glacé de la maison, avec un sirop de saison au choix : épices d'automne, pomme crumble ou caramel salé.",
       en_d="The house iced matcha with your choice of seasonal syrup: autumn spice, apple crumble or salted caramel.", en_name="Iced Zaytouna Matcha"),
  dict(id="matcha-cb", cat="matchas", name="Matcha Crème Brûlée Glacé", fr="matcha-creme-brulee-glace", en="iced-creme-brulee-matcha", price=10.45,
       fr_d="Matcha glacé coiffé d'une crème brûlée caramélisée.", en_d="Iced matcha crowned with a caramelized crème brûlée top.",
       en_name="Iced Crème Brûlée Matcha", photo="matcha-creme-brulee", star=True),
  dict(id="matcha-fraise", cat="matchas", name="Matcha Fraise", fr="matcha-fraise", en="strawberry-matcha", price=9.75,
       fr_d="Le matcha rencontre la fraise.", en_d="Matcha meets strawberry.", en_name="Strawberry Matcha", star=True),
  dict(id="matcha-framboise", cat="matchas", name="Matcha Framboise", fr="matcha-framboise", en="raspberry-matcha", price=9.75,
       fr_d="Le matcha rencontre la framboise.", en_d="Matcha meets raspberry.", en_name="Raspberry Matcha"),
  dict(id="matcha-mangue", cat="matchas", name="Matcha Mangue", fr="matcha-mangue", en="mango-matcha", price=9.75,
       fr_d="Le matcha rencontre la mangue.", en_d="Matcha meets mango.", en_name="Mango Matcha"),
  dict(id="matcha-pistache", cat="matchas", name="Matcha Pistache Glacé", fr="matcha-pistache-glace", en="iced-pistachio-matcha", price=9.75,
       fr_d="Matcha glacé à la pistache.", en_d="Iced matcha with pistachio.", en_name="Iced Pistachio Matcha", nuts=True, star=True),
  dict(id="matcha-biscoff", cat="matchas", name="Matcha Biscoff Glacé", fr="matcha-biscoff-glace", en="iced-biscoff-matcha", price=9.75,
       fr_d="Matcha glacé aux saveurs de biscuit Biscoff.", en_d="Iced matcha with Biscoff cookie flavour.", en_name="Iced Biscoff Matcha"),
  dict(id="latte-cb", cat="lattes", name="Latte Crème Brûlée Glacé", fr="latte-creme-brulee-glace", en="iced-creme-brulee-latte", price=9.45,
       fr_d="Latte glacé surmonté d'une crème brûlée caramélisée.", en_d="Iced latte topped with a caramelized crème brûlée layer.",
       en_name="Iced Crème Brûlée Latte", photo="latte-creme-brulee", star=True),
  dict(id="latte-biscoff", cat="lattes", name="Latte Biscoff Glacé", fr="latte-biscoff-glace", en="iced-biscoff-latte", price=8.75,
       fr_d="Latte glacé aux saveurs de biscuit Biscoff.", en_d="Iced latte with Biscoff cookie flavour.", en_name="Iced Biscoff Latte", star=True),
  dict(id="limonade-framboise", cat="limonades", name="Limonade Framboise", fr="limonade-framboise", en="raspberry-lemonade", price=8.50,
       fr_d="Notre limonade à la framboise.", en_d="Our raspberry lemonade.", en_name="Raspberry Lemonade"),
  dict(id="wrap-chipotle", cat="sandwichs", name="Sandwich Wrap Chipotle", fr="wrap-chipotle", en="chipotle-wrap", price=11.45,
       fr_d="Un wrap aux saveurs de chipotle.", en_d="A chipotle-flavoured wrap.", en_name="Chipotle Wrap", star=True),
  dict(id="wrap-cesar", cat="sandwichs", name="Sandwich Wrap César", fr="wrap-cesar", en="caesar-wrap", price=11.45,
       fr_d="Un wrap façon César.", en_d="A Caesar-style wrap.", en_name="Caesar Wrap"),
  dict(id="poulet-bbq", cat="sandwichs", name="Sandwich Poulet BBQ", fr="sandwich-poulet-bbq", en="bbq-chicken-sandwich", price=13.25,
       fr_d="Sandwich au poulet BBQ.", en_d="BBQ chicken sandwich.", en_name="BBQ Chicken Sandwich"),
  dict(id="cb-vanille", cat="cremes", name="Crème Brûlée Vanille", fr="creme-brulee-vanille", en="vanilla-creme-brulee", price=8.10,
       fr_d="La crème brûlée classique à la vanille.", en_d="Classic vanilla crème brûlée.", en_name="Vanilla Crème Brûlée", star=True),
]

# Google reviews supplied by the owner (original text, English). Truncated reviews end with "…".
REVIEWS = [
  ("Farah", "Such a nice and peaceful coffee shop. I came with my husband, i got a sandwich and the crème brûlée matcha and he got the cortado. Everything was just so good!! The crème brûlée topping on the matcha was just delicious and the cortado was perfectly balanced (just enough milk). The staff was super friendly yet professional.", ["matcha-cb"]),
  ("Olivia Lapia", "Came here after an appointment and had no idea I was about to discover one of my new favorite coffee spots! 🤍 The Crème Brûlée Latte with oat milk was hands down one of the best coffees I’ve ever had. The breakfast sandwich was so fresh and…", ["latte-cb"]),
  ("Humairaa Bukhari", "Great new café in the area! The iced crème brûlée latte was amazing and the crème brûlée is one of the best I’ve had in Montreal! Such cute decor and a nice majlis-style floor seating area. Will definitely return!", ["latte-cb", "cb-vanille", "cafe"]),
  ("Timothy Ho", "Nice cozy cafe. Great seating inside and outside. I ordered an iced matcha latte with vanilla and it tasted great. Service was good. They had some good pastries on display so I might come back again to try them. Very charming decor and the…", ["matcha-latte"]),
  ("Sepideh Sabati", "Went in for a little coffee. Loved the ambiance. They did a great job with the decor and vibe in there. And the menu reflects that too. I got the speciality latte (qahwah latte - maple and cardamom) and it was delicious! The barista…", []),
  ("Aymen sohail", "I visited Cafe Zaytouna during my stay in Montreal and absolutely loved it. I tried their crème brûlée matcha, and it was so good. I came with a large group, and the seating area was very spacious. My siblings also tried a few of their…", ["matcha-cb"]),
  ("Aya Salah", "I loved the whole vibe of this quaint cafe: the theme, decor, ambiance. I had a Qahwa Latte (SPECTACULAR) and a Nutella cookie that had so much more flavour than its name. Definitely a gem of a place.", []),
  ("Chiara Marando", "Thank God finally a matcha spot near me!!! 10/10 would recommend the creme brûlée matcha. The staff was sooo so friendly and kind. 🥰 Nice seating area to chill with your friends or study. Definitely a coffee shop you can’t miss!!", ["matcha-cb"]),
  ("S. M.", "Service is good. Good customer service. Very good coffee. Highly recommend biscoff latte. From America came here every morning while staying here.", ["latte-biscoff"]),
  ("Tohidul Haque", "Everything is so nice. From the food all the way to the vybe and the staff warm welcome. Definitely coming back as i didnt try everything on the menu.", []),
  ("Halimah Hussaini", "Fantastic cafe with good service and good food. I'll be definitely visiting again soon", []),
  ("Anum Noreen", "I tried the hibiscus latter with the strawberry cheesecake. It was really good. The food proprtion was really good. I got full just with that. Moreover, there are a lot of charging ports and no music which is great for studying.", ["cafe"]),
  ("anika ahmed", "Beautiful and cozy café! The crème brûlée matcha was the perfect drink to satisfy my sweet tooth. Bonus it’s right next to the metro station, so there’s not much walking if it’s a cold day outside 🤍", ["matcha-cb", "visit"]),
  ("Noor Khebir", "I went for coffee with my friend and honestly had such a great experience. The staff were incredibly kind, and one of the staff members (I think maybe the owner’s father) noticed we were sitting on the older chairs and personally switched…", []),
  ("Ghizlane Z.", "They make everything from scratch! Service is super great and the drinks taste clean and good! The decor is really intentional referencing cultural and religious points of inspiration. 🤍", ["cafe"]),
  ("Snokes", "Great first visit today. I had the fig matcha and bbq poulet panini. 10/10 😍 Highly recommend!", ["poulet-bbq"]),
  ("queen meso", "The most comfy cafe🤍 the workers are very polite…", []),
  ("Mahmoud Abdel Basset", "Great service and set up. The Qahwa latte and crème brûlée latte are a must try.", ["latte-cb"]),
  ("Zainab A.", "Café Zaytouna is becoming one of my favourite spots in Montreal 🫒 🍃 I always love staying there and relaxing while enjoying the delicious variety of desserts and distinguished drinks they have!", ["cafe"]),
  ("Adam", "Visited this coffee shop with my fiance and what an experience. The staff was so welcoming and gave us great suggestions for drinks and food. It all tasted amazing and felt very comfortable. Highly suggest this place to everyone.", []),
  ("cayla britzolakis", "Such a nice café! Soo cute, amazing service and the energy was so pure. Loved the fact that they have tea and have oat milk and lactose free milk! So many options to choose from. Glad to finally have a café like this in the area.", ["cafe"]),
  ("mrk009", "Amazing creme brulé. All the flavours are to die for, especially the raspberry one. Matcha Latte also very solid. Definitely recommend to everyone.", ["cb-vanille", "matcha-latte"]),
  ("Dalya_ MD", "Matcha & Lemonade were excellent! Took also their creme brulée and it was exquisite. Amazing service as well :) definitely my new cafe spot 🙌🏻", ["cb-vanille"]),
  ("Zeinab khanafer", "Amazing crème brûlée latte and staff :) beautiful cafe", ["latte-cb"]),
  ("Winnie Naphan", "missed by bus and stopped by here to wait for it and was shocked by the ambiance, food and coffee quality.", []),
]

PHOTOS = {  # key: (width, height, alt_fr, alt_en)
  "coin-salon": (1079, 1440, "Coin salon de Café Zaytouna : banquettes basses vertes à motifs tissés, olivier en pot et grande fenêtre sur la rue",
                 "Café Zaytouna lounge corner: low green floor seating with woven patterns, a potted olive tree and a large street-facing window"),
  "matcha-creme-brulee": (1068, 1438, "Matcha glacé surmonté d'une crème brûlée caramélisée, tenu devant l'olivier du café",
                          "Iced crème brûlée matcha held up in front of the café's olive tree"),
  "latte-creme-brulee": (1079, 1176, "Latte glacé à la crème brûlée sur un plateau en bois, près d'une rôtie à l'avocat",
                         "Iced crème brûlée latte on a wooden tray next to avocado toast"),
  "salle": (1079, 814, "Salle lumineuse de Café Zaytouna : tables en bois clair, chaises vertes matelassées, miroirs et tapis mural",
            "Bright Café Zaytouna dining room with light wood tables, quilted green chairs, mirrors and a wall rug"),
  "comptoir": (1080, 1440, "Comptoir en bois à lattes, menus muraux et vitrine réfrigérée de gâteaux et pâtisseries",
               "Slatted wood counter, wall menus and a refrigerated display of cakes and pastries"),
  "facade-soir": (1079, 1440, "Vitrine de Café Zaytouna le soir avec le logo, guirlandes lumineuses et petite terrasse",
                  "Café Zaytouna's window at night with the logo, string lights and a small terrace"),
  "cheesecake": (1080, 1440, "Part de gâteau au fromage nappé de fraises et café glacé sur un plateau en bois",
                 "Slice of strawberry-topped cheesecake and an iced coffee on a wooden tray"),
  "plateau-limonades": (1079, 1437, "Deux boissons violettes garnies d'agrumes séchés et deux desserts en verrine, vus du dessus",
                        "Two purple drinks garnished with dried citrus and two desserts in glasses, seen from above"),
  "duo-glaces": (1079, 1442, "Une boisson glacée au matcha et une boisson glacée au chocolat sur une banquette à motifs verts",
                 "An iced matcha drink and an iced chocolate drink on green patterned floor seating"),
}

# =========================== HELPERS ===========================
E = html.escape
ITEM = {i["id"]: i for i in ITEMS}
CAT = {c["id"]: c for c in CATS}

def price(v, lang):
    return f"{v:.2f}".replace(".", ",") + " $" if lang == "fr" else f"${v:.2f}"

def hfmt(h, lang):
    if lang == "fr": return f"{h} h"
    s = "a.m." if h < 12 else "p.m."
    return f"{h if h <= 12 else h - 12} {s}"

def hours_txt(o, c, lang): return f"{hfmt(o, lang)} – {hfmt(c, lang)}"

def fit(text, n=160):
    if len(text) <= n: return text
    cut = text[: n - 1].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"

def iname(i, lang): return i["name"] if lang == "fr" else i["en_name"]

# Page registry: key -> {fr: path, en: path}
PAGES = {
  "home": {"fr": "index.html", "en": "en/index.html"},
  "menu": {"fr": "menu.html", "en": "en/menu.html"},
  "cafe": {"fr": "le-cafe.html", "en": "en/the-cafe.html"},
  "reviews": {"fr": "avis.html", "en": "en/reviews.html"},
  "visit": {"fr": "nous-trouver.html", "en": "en/find-us.html"},
  "privacy": {"fr": "politique-de-confidentialite.html", "en": "en/privacy-policy.html"},
  "terms": {"fr": "conditions-utilisation.html", "en": "en/terms-of-use.html"},
}
for i in ITEMS:
    PAGES["item:" + i["id"]] = {"fr": f"menu/{i['fr']}.html", "en": f"en/menu/{i['en']}.html"}

def rel(from_path, to_path):
    depth = from_path.count("/")
    return "../" * depth + to_path

def absurl(path):
    return SITE_URL + "/" + ("" if path == "index.html" else path.replace("index.html", ""))

_data_cache = {}
def asset(cur, name):
    """URL for an asset file — data URI in preview mode."""
    if PREVIEW:
        if name not in _data_cache:
            p = ROOT / "assets" / name
            mime = "image/webp" if name.endswith(".webp") else "image/png"
            _data_cache[name] = f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()
        return _data_cache[name]
    return rel(cur, "assets/" + name)

def _desk(sizes):
    last = sizes.split(",")[-1].strip()
    return last if last.endswith(("px", "vw")) else "520px"

def picture(cur, base, widths, sizes, attrs):
    """<picture> with AVIF first, WebP fallback. base = 'img/coin-salon' (files base-480.avif ...)."""
    av = ", ".join(f"{asset(cur, f'{base}-{w}.avif')} {w}w" for w in widths)
    wb = ", ".join(f"{asset(cur, f'{base}-{w}.webp')} {w}w" for w in widths)
    mid = widths[len(widths) // 2]
    return (f'<picture><source type="image/avif" srcset="{av}" sizes="{sizes}">'
            f'<img src="{asset(cur, f"{base}-{mid}.webp")}" srcset="{wb}" sizes="{sizes}" {attrs}></picture>')

def img(cur, key, lang, sizes="100vw", eager=False, cls="", style="", alt=None, large=True, small=False):
    w, h, afr, aen = PHOTOS[key]
    a = alt if alt is not None else (afr if lang == "fr" else aen)
    attrs = [f'width="{w}" height="{h}"', f'alt="{E(a)}"']
    if eager: attrs.append('fetchpriority="high" decoding="async"')
    else: attrs.append('loading="lazy" decoding="async" fetchpriority="low"')
    if cls: attrs.append(f'class="{cls}"')
    if style: attrs.append(f'style="{style}"')
    if PREVIEW:
        src = asset(cur, f"{key}.webp" if large else f"{key}-sm.webp")
        return f'<img src="{src}" {" ".join(attrs)}>'
    # Phones get ~2.2x density (sharp, but far lighter than full 3x files)
    sz = "180px" if small else f"(max-width: 600px) 260px, (max-width: 960px) 420px, {_desk(sizes)}"
    return picture(cur, f"img/{key}", (480, 800, 1100), sz, " ".join(attrs))

def logo_img(cur, px, cls, alt, lazy=False):
    if PREVIEW:
        return f'<img class="{cls}" src="{asset(cur, "logo-zaytouna-192.png")}" width="{px}" height="{px}" alt="{alt}">'
    lz = ' loading="lazy"' if lazy else ""
    return picture(cur, "img/logo", (104, 232), f"{px}px", f'class="{cls}" width="{px}" height="{px}" alt="{alt}" decoding="async"{lz}')

ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'
STAR_PATH = "M12 2.8l2.8 5.7 6.3.9-4.5 4.4 1.1 6.2L12 17l-5.7 3 1.1-6.2L2.9 9.4l6.3-.9z"
_sid = [0]
def stars(value=RATING):
    out = []
    for k in range(5):
        f = max(0, min(1, value - k)); _sid[0] += 1; gid = f"s{_sid[0]}"
        out.append(f'<svg viewBox="0 0 24 24"><defs><linearGradient id="{gid}"><stop offset="{f*100:.0f}%" stop-color="currentColor"/>'
                   f'<stop offset="{f*100:.0f}%" stop-color="currentColor" stop-opacity=".28"/></linearGradient></defs><path fill="url(#{gid})" d="{STAR_PATH}"/></svg>')
    return f'<span class="stars" aria-hidden="true">{"".join(out)}</span>'

def rating_text(lang):
    r = f"{RATING:.1f}".replace(".", ",") if lang == "fr" else f"{RATING:.1f}"
    return f"{r}/5 · {REVIEW_COUNT} avis Google" if lang == "fr" else f"{r}/5 · {REVIEW_COUNT} Google reviews"

def btn(href, label, cls="btn", ext=True, arrow=True, extra=""):
    t = ' target="_blank" rel="noopener"' if ext else ""
    return f'<a class="{cls}" href="{E(href)}"{t}{extra}><span>{label}</span>{ARROW if arrow else ""}</a>'

T = {
  "fr": dict(order="Commander maintenant", order_short="Commander", directions="Obtenir l'itinéraire", menu="Menu", cafe="Le café",
             reviews="Avis", visit="Nous trouver", home="Accueil", skip="Aller au contenu", see_menu="Voir le menu et commander",
             read_google="Lire les avis sur Google", leave_review="Laisser un avis", open_menu="Ouvrir le menu", close_menu="Fermer le menu",
             switch="EN", switch_label="English version", address="Adresse", hours="Heures d'ouverture", phone="Téléphone",
             today="Aujourd'hui", rights="Tous droits réservés.", follow="Suivez-nous", nav="Navigation", order_uber="Commander sur Uber Eats",
             orig="Avis Google, texte original en anglais", open_now="Ouvert maintenant · ferme à {c}", closed_now="Fermé · ouvre {d} à {o}",
             closed_today="aujourd'hui", closed_tomorrow="demain", all_menu="Tout le menu", logo_alt="Logo Café Zaytouna",
             price_note="Prix affichés sur Uber Eats en octobre 2026, avant taxes et frais. Ils peuvent changer.",
             final_t="Votre pause Zaytouna vous attend.", final_d="Découvrez le menu et choisissez votre prochaine gourmandise.",
             invite_t="Vous avez aimé votre café ou votre repas?", invite_d="Partagez votre expérience. Votre avis compte pour Café Zaytouna.",
             addr_html="8762, rue Lajeunesse<br>Montréal (Québec) H2M 1R6", addr_line="8762, rue Lajeunesse, Montréal",
             nuts="Contient des noix", category="Catégorie", also="Aussi dans cette catégorie", what_say="Ce qu'en disent nos clients",
             visit_us="Venez nous voir", open_maps="Ouvrir dans Google Maps", call="Appeler", privacy="Politique de confidentialité", terms="Conditions d’utilisation", show_map="Afficher la carte", map_note="La carte est fournie par Google. En l’affichant, vous acceptez que Google reçoive des données de connexion.", updated="Dernière mise à jour", legal="Informations légales"),
  "en": dict(order="Order now", order_short="Order", directions="Get directions", menu="Menu", cafe="The café",
             reviews="Reviews", visit="Find us", home="Home", skip="Skip to content", see_menu="See the menu and order",
             read_google="Read the reviews on Google", leave_review="Leave a review", open_menu="Open menu", close_menu="Close menu",
             switch="FR", switch_label="Version française", address="Address", hours="Opening hours", phone="Phone",
             today="Today", rights="All rights reserved.", follow="Follow us", nav="Navigation", order_uber="Order on Uber Eats",
             orig="Google review", open_now="Open now · closes at {c}", closed_now="Closed · opens {d} at {o}",
             closed_today="today", closed_tomorrow="tomorrow", all_menu="Full menu", logo_alt="Café Zaytouna logo",
             price_note="Prices as listed on Uber Eats in October 2026, before taxes and fees. Subject to change.",
             final_t="Your Zaytouna break is waiting.", final_d="Explore the menu and choose your next treat.",
             invite_t="Enjoyed your coffee or meal?", invite_d="Share your experience. Your review matters to Café Zaytouna.",
             addr_html="8762 Rue Lajeunesse<br>Montréal, QC H2M 1R6", addr_line="8762 Rue Lajeunesse, Montréal",
             nuts="Contains nuts", category="Category", also="More in this category", what_say="What our guests say",
             visit_us="Come visit", open_maps="Open in Google Maps", call="Call", privacy="Privacy policy", terms="Terms of use", show_map="Show the map", map_note="The map is provided by Google. By showing it, you agree that Google receives connection data.", updated="Last updated", legal="Legal"),
}

def business_ld():
    return {
      "@type": "CafeOrCoffeeShop", "@id": SITE_URL + "/#cafe", "name": NAME, "url": SITE_URL + "/",
      "image": SITE_URL + "/assets/img/coin-salon-1100.webp", "logo": SITE_URL + "/assets/logo-zaytouna-512.png",
      "telephone": PHONE_E164, "priceRange": "$",
      "address": {"@type": "PostalAddress", "streetAddress": "8762 Rue Lajeunesse", "addressLocality": "Montréal",
                  "addressRegion": "QC", "postalCode": "H2M 1R6", "addressCountry": "CA"},
      "geo": {"@type": "GeoCoordinates", "latitude": GEO[0], "longitude": GEO[1]},
      "hasMap": MAPS_URL, "sameAs": [INSTAGRAM], "servesCuisine": ["Café", "Matcha", "Desserts"],
      "menu": SITE_URL + "/menu.html", "acceptsReservations": False,
      "openingHoursSpecification": [{"@type": "OpeningHoursSpecification", "dayOfWeek": SCHEMA_DAYS[k],
                                     "opens": f"{o:02d}:00", "closes": f"{c:02d}:00"} for k, (o, c) in enumerate(HOURS)],
      "potentialAction": {"@type": "OrderAction", "target": ORDER_URL},
    }

def breadcrumb_ld(trail):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": n + 1, "name": name, "item": absurl(path)} for n, (name, path) in enumerate(trail)]}

def crumbs_html(cur, trail, lang):
    lis = []
    for n, (name, path) in enumerate(trail):
        if n == len(trail) - 1: lis.append(f'<li><span aria-current="page">{E(name)}</span></li>')
        else: lis.append(f'<li><a href="{rel(cur, path)}">{E(name)}</a></li>')
    return f'<nav class="crumbs wrap" aria-label="{"Fil d’Ariane" if lang == "fr" else "Breadcrumb"}"><ol>{"".join(lis)}</ol></nav>'

def hours_table(lang):
    rows = "".join(f'<tr data-day="{k}"><th scope="row">{DAYS[lang][k]}</th><td>{hours_txt(o, c, lang)}</td></tr>' for k, (o, c) in enumerate(HOURS))
    return f'<table class="hours-table"><caption class="sr">{T[lang]["hours"]}</caption><tbody>{rows}</tbody></table>'

def open_status(lang):
    t = T[lang]
    data = E(json.dumps({"h": HOURS, "lang": lang, "open": t["open_now"], "closed": t["closed_now"],
                         "today": t["closed_today"], "tomorrow": t["closed_tomorrow"], "days": DAYS[lang]}))
    return f'<span class="open-status" data-open-status="{data}" aria-live="polite"></span>'

def quote(r, lang, cls=""):
    who, text, _ = r
    note = T[lang]["orig"]
    return (f'<figure class="quote {cls} reveal"><blockquote lang="en"><p>“{E(text)}”</p></blockquote>'
            f'<figcaption>{stars(5)}<span><span class="quote__who">{E(who)}</span> · {note}</span></figcaption></figure>')

def reviews_for(tag): return [r for r in REVIEWS if tag in r[2]]

# =========================== LAYOUT ===========================
def font_url(name):
    if PREVIEW:
        return "data:font/woff;base64," + base64.b64encode((ROOT / "assets/fonts" / name).read_bytes()).decode()
    return "assets/fonts/" + name  # relative to styles.css at the site root
FONT_CSS = (f'@font-face{{font-family:"Marcellus";font-style:normal;font-weight:400;font-display:swap;src:url("{font_url("marcellus-latin.woff")}") format("woff")}}'
            f'@font-face{{font-family:"Figtree";font-style:normal;font-weight:400 700;font-display:swap;src:url("{font_url("figtree-latin-var.woff")}") format("woff")}}\n')
CSS = FONT_CSS + (ROOT / "base.css").read_text(encoding="utf-8") + (ROOT / "extra.css").read_text(encoding="utf-8")
CSP = ("default-src 'none'; script-src 'self' 'inline-speculation-rules'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
       "frame-src https://www.google.com; connect-src 'self'; manifest-src 'self'; base-uri 'none'; form-action 'none'; "
       "object-src 'none'; upgrade-insecure-requests")
OG = {"home": "og-home", "menu": "og-salle", "cafe": "og-home", "reviews": "og-latte", "visit": "og-facade", "privacy": "og-home", "terms": "og-home"}
JS = (ROOT / "site.js").read_text(encoding="utf-8")

SPEC = ('<script type="speculationrules">' + json.dumps({"prerender": [
    {"where": {"selector_matches": ".langs a"}, "eagerness": "eager"},
    {"where": {"and": [{"href_matches": "/*"}, {"not": {"selector_matches": "[target=_blank]"}}]}, "eagerness": "moderate"}]}) + "</script>")

def lcp_preload(cur, key):
    """Start downloading the main hero photo right away (AVIF, same choice the page will make)."""
    if PREVIEW: return ""
    photo = {"home": "coin-salon"}.get(key) or (ITEM[key[5:]].get("photo") if key.startswith("item:") else None)
    if not photo: return ""
    srcset = ", ".join(f"{asset(cur, f'img/{photo}-{w}.avif')} {w}w" for w in (480, 800, 1100))
    return (f'\n<link rel="preload" as="image" type="image/avif" imagesrcset="{srcset}" '
            f'imagesizes="(max-width: 600px) 260px, (max-width: 960px) 420px, 520px" fetchpriority="high">')

def layout(cur, key, lang, title, desc, body, ld_extra=(), og_image=None, active=None, robots="index,follow,max-image-preview:large"):
    og_image = og_image or OG.get(key, "og-home")
    t = T[lang]
    other = "en" if lang == "fr" else "fr"
    alt_path = PAGES[key][other]
    def nav_link(k):
        cur_attr = ' aria-current="page"' if active == k else ""
        return f'<a href="{rel(cur, PAGES[k][lang])}"{cur_attr}>{t[k]}</a>'
    navs = "".join(nav_link(k) for k in ("menu", "cafe", "reviews", "visit"))
    mnavs = "".join(f"<li>{nav_link(k)}</li>" for k in ("menu", "cafe", "reviews", "visit"))
    logo = asset(cur, "logo-zaytouna-192.png")
    graph = {"@context": "https://schema.org", "@graph": [business_ld(), *ld_extra]}
    hreflang = "".join(f'<link rel="alternate" hreflang="{h}" href="{absurl(PAGES[key][l])}">'
                       for h, l in (("fr-CA", "fr"), ("en-CA", "en"), ("x-default", "fr")))
    if PREVIEW:
        icons = f'<link rel="icon" type="image/png" href="{logo}">'
    else:
        icons = (f'<meta http-equiv="Content-Security-Policy" content="{CSP}">\n<meta name="referrer" content="strict-origin-when-cross-origin">\n'
                 f'<link rel="icon" href="{rel(cur, "favicon.ico")}" sizes="any">\n<link rel="icon" type="image/png" sizes="32x32" href="{rel(cur, "assets/favicon-32.png")}">\n'
                 f'<link rel="apple-touch-icon" href="{rel(cur, "assets/apple-touch-icon.png")}">\n<link rel="manifest" href="{rel(cur, "site.webmanifest")}">\n'
                 f'<link rel="preload" href="{rel(cur, "assets/fonts/marcellus-latin.woff")}" as="font" type="font/woff" crossorigin>\n'
                 f'<link rel="preload" href="{rel(cur, "assets/fonts/figtree-latin-var.woff")}" as="font" type="font/woff" crossorigin>')
    style = f"<style>{CSS}</style>" if PREVIEW else f'<link rel="stylesheet" href="{rel(cur, "styles.css")}">'
    script = f"<script>{JS}</script>" if PREVIEW else f'<script src="{rel(cur, "site.js")}" defer></script>'
    head = f"""<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{absurl(PAGES[key][lang])}">
{hreflang}
<meta property="og:type" content="website">
<meta property="og:site_name" content="{NAME}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{absurl(PAGES[key][lang])}">
<meta property="og:image" content="{SITE_URL}/assets/{og_image}.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{NAME}">
<meta name="robots" content="{robots}">
<meta property="og:locale" content="{'fr_CA' if lang == 'fr' else 'en_CA'}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#183F1B">
{icons}
<script type="application/ld+json">{json.dumps(graph, ensure_ascii=False)}</script>
{lcp_preload(cur, key)}
{style}"""
    order_btn = f'<a class="btn btn--order-desktop" href="{ORDER_URL}" target="_blank" rel="noopener">{t["order"]}</a>'
    body_html = f"""<a class="skip" href="#main">{t['skip']}</a>
<header class="header" id="top">
  <div class="wrap header__in">
    <a class="brand" href="{rel(cur, PAGES['home'][lang])}" aria-label="{NAME} — {t['home']}">
      {logo_img(cur, 52, 'brand__logo', t['logo_alt'])}<span><small>Café</small>Zaytouna</span>
    </a>
    <nav class="nav" aria-label="{'Navigation principale' if lang == 'fr' else 'Main navigation'}">{navs}</nav>
    <div class="header__actions">
      <nav class="langs" aria-label="{'Langue' if lang == 'fr' else 'Language'}">
        {('<span aria-current="true" lang="fr">FR</span><a href="' + rel(cur, alt_path) + '" hreflang="en" lang="en" aria-label="English version">EN</a>') if lang == 'fr'
          else ('<a href="' + rel(cur, alt_path) + '" hreflang="fr" lang="fr" aria-label="Version française">FR</a><span aria-current="true" lang="en">EN</span>')}
      </nav>
      {order_btn}
      <button class="menu-toggle" type="button" id="menu-toggle" aria-expanded="false" aria-controls="mobile-nav" aria-label="{t['open_menu']}" data-open-label="{t['open_menu']}" data-close-label="{t['close_menu']}"><span></span></button>
    </div>
  </div>
</header>
<nav class="mobile-nav" id="mobile-nav" aria-label="{'Navigation mobile' if lang == 'fr' else 'Mobile navigation'}">
  <ul>{mnavs}<li class="mobile-nav__lang"><a href="{rel(cur, alt_path)}" hreflang="{other}" lang="{other}">{'English version' if lang == 'fr' else 'Version française'}</a></li><li><a class="btn btn--lg" href="{ORDER_URL}" target="_blank" rel="noopener">{t['order']}</a></li></ul>
</nav>
<main id="main">
{body}
{final_cta(cur, lang)}
</main>
{footer(cur, lang)}
<div class="order-bar" id="order-bar" aria-hidden="true">{btn(ORDER_URL, t['order_short'], 'btn btn--lg', extra=' tabindex="-1"')}</div>
{script}"""
    return head, body_html

def final_bg(cur):
    if PREVIEW: return img(cur, 'facade-soir', 'fr', alt='', large=False)
    return (f'<picture><source type="image/avif" srcset="{asset(cur, "img/final-bg.avif")}">'
            f'<img src="{asset(cur, "img/final-bg.webp")}" width="560" height="747" alt="" loading="lazy" decoding="async" fetchpriority="low"></picture>')

def final_cta(cur, lang):
    t = T[lang]
    return f"""<section class="final on-band" id="commander" aria-labelledby="final-title">
  <div class="final__bg" aria-hidden="true">{final_bg(cur)}</div>
  <div class="wrap"><div class="final__in reveal">
    <div class="kilim" aria-hidden="true" style="width:160px"></div>
    <h2 id="final-title">{t['final_t']}</h2><p>{t['final_d']}</p>
    <div class="final__ctas">{btn(ORDER_URL, t['order'], 'btn btn--light btn--lg')}
      {btn(rel(cur, PAGES['visit'][lang]), t['directions'], 'btn btn--outline-light btn--lg', ext=False, arrow=False)}</div>
  </div></div>
</section>
<section class="review-invite" aria-labelledby="invite-title"><div class="wrap"><div class="invite reveal">
  <div class="invite__mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="{STAR_PATH}"/></svg></div>
  <div><h2 id="invite-title">{t['invite_t']}</h2><p>{t['invite_d']}</p></div>
  {btn(REVIEW_URL, t['leave_review'], 'btn btn--ghost btn--lg', arrow=False)}
</div></div></section>"""

def footer(cur, lang):
    t = T[lang]
    hrs = "".join(f"<li>{DAYS[lang][k][:3]}. {hours_txt(o, c, lang)}</li>" for k, (o, c) in enumerate(HOURS))
    navs = "".join(f'<li><a href="{rel(cur, PAGES[k][lang])}">{t[k]}</a></li>' for k in ("home", "menu", "cafe", "reviews", "visit"))
    return f"""<footer class="footer"><div class="wrap">
  <div class="footer__grid">
    <div class="footer__brand">{logo_img(cur, 116, 'footer__logo', t['logo_alt'], lazy=True)}</div>
    <div><h3>{t['address']}</h3><address>{t['addr_html']}</address>
      <p style="margin-top:.6rem"><a class="tel" href="tel:{PHONE_E164}">{PHONE[lang]}</a></p>
      <p style="margin-top:.6rem"><a class="link" href="{rel(cur, PAGES['visit'][lang])}">{t['directions']}</a></p></div>
    <div><h3>{t['hours']}</h3><ul>{hrs}</ul></div>
    <div><h3>{t['nav']}</h3><ul>{navs}
      <li><a href="{INSTAGRAM}" target="_blank" rel="noopener">Instagram · @cafezaytouna</a></li>
      <li><a href="{ORDER_URL}" target="_blank" rel="noopener">{t['order_uber']}</a></li>
      <li><a href="{REVIEW_URL}" target="_blank" rel="noopener">{t['leave_review']}</a></li></ul></div>
  </div>
  <div class="footer__bottom"><span>© <span data-year>2026</span> {NAME}. {t['rights']}</span>
    <span class="footer__legal"><a href="{rel(cur, PAGES['privacy'][lang])}">{t['privacy']}</a> · <a href="{rel(cur, PAGES['terms'][lang])}">{t['terms']}</a></span></div>
</div></footer>"""

# =========================== PAGES ===========================
def item_link(cur, i, lang): return rel(cur, PAGES["item:" + i["id"]][lang])

def page_home(lang):
    cur = PAGES["home"][lang]; t = T[lang]
    fr = lang == "fr"
    feat = [ITEM["matcha-cb"], ITEM["latte-cb"]]
    board = [ITEM[k] for k in ("matcha-fraise", "matcha-pistache", "wrap-chipotle", "cb-vanille")]
    feats = ""
    for i in feat:
        feats += f"""<a class="feature reveal" href="{item_link(cur, i, lang)}">
  <div class="feature__img">{img(cur, i['photo'], lang, '(max-width: 600px) 92vw, 46vw')}</div>
  <div class="feature__row"><h3>{iname(i, lang)}</h3><span class="price">{price(i['price'], lang)}</span></div>
  <p>{i['fr_d'] if fr else i['en_d']}</p>
  <span class="feature__cta"><span>{'Voir le produit' if fr else 'View item'}</span>{ARROW}</span></a>"""
    rows = "".join(f"""<li><a href="{item_link(cur, i, lang)}"><span class="board__name">{iname(i, lang)}</span><span class="price">{price(i['price'], lang)}</span>
      <span class="board__desc">{i['fr_d'] if fr else i['en_d']}{(' ' + t['nuts'] + '.') if i.get('nuts') else ''}</span></a></li>""" for i in board)
    q3 = "".join(quote(r, lang) for r in (REVIEWS[0], REVIEWS[1], REVIEWS[2]))
    body = f"""
<section class="hero" aria-labelledby="hero-title"><div class="wrap hero__grid">
  <div class="hero__text">
    <span class="eyebrow">{t['addr_line'].replace(', Montréal', ' · Montréal')}</span>
    <h1 id="hero-title">{'Votre prochaine pause café <em>commence ici.</em>' if fr else 'Your next coffee break <em>starts here.</em>'}</h1>
    <p class="hero__lede">{'Cafés, matchas et gourmandises à savourer chez Café Zaytouna, à Montréal.' if fr else 'Coffee, matcha and treats to enjoy at Café Zaytouna in Montréal.'}</p>
    <div class="hero__ctas" id="hero-ctas">{btn(ORDER_URL, t['order'], 'btn btn--lg')}
      <a class="btn btn--ghost btn--lg" href="{rel(cur, PAGES['menu'][lang])}">{'Découvrir le menu' if fr else 'Explore the menu'}</a></div>
    <a class="rating" href="{rel(cur, PAGES['reviews'][lang])}"><span class="rating__g" aria-hidden="true">G</span>{stars()}<span class="rating__txt">{rating_text(lang)}</span></a>
  </div>
  <div class="hero__media">
    <div class="arch">{img(cur, 'coin-salon', lang, '(max-width: 960px) 92vw, 520px', eager=True)}</div>
    <div class="ring">{img(cur, 'matcha-creme-brulee', lang, '220px', large=False, small=True)}</div>
    <p class="hero__note" aria-hidden="true"><b>Zaytouna</b><span>{'« olive », en arabe' if fr else '“olive” in Arabic'}</span></p>
  </div>
</div></section>
<div class="kilim" aria-hidden="true"></div>

<section class="section" aria-labelledby="menu-title"><div class="wrap">
  <div class="section__head reveal"><span class="eyebrow">{'Sur notre carte' if fr else 'From our menu'}</span>
    <h2 id="menu-title">{'Des boissons et gourmandises à découvrir' if fr else 'Drinks and treats worth discovering'}</h2>
    <p>{'Matchas, lattes signatures, sandwichs et crèmes brûlées. Les deux boissons dont nos clients parlent le plus :' if fr else 'Matcha, signature lattes, sandwiches and crème brûlée. The two drinks our guests mention most:'}</p></div>
  <div class="features">{feats}</div>
  <div class="board">
    <div class="board__intro reveal"><h3>{'Aussi au menu' if fr else 'Also on the menu'}</h3>
      <p>{'Quelques autres incontournables, du matcha à la crème brûlée.' if fr else 'A few more essentials, from matcha to crème brûlée.'}</p>
      <p style="display:flex;flex-wrap:wrap;gap:.6rem"><a class="btn" href="{rel(cur, PAGES['menu'][lang])}"><span>{t['all_menu']}</span>{ARROW}</a>
        {btn(ORDER_URL, t['order_short'], 'btn btn--ghost', arrow=False)}</p>
      <p class="fineprint">{t['price_note']}</p></div>
    <ul class="board__list reveal">{rows}</ul>
  </div>
</div></section>

<section class="section exp" aria-labelledby="cafe-title"><div class="wrap split">
  <div class="split__img reveal">{img(cur, 'salle', lang, '(max-width: 960px) 92vw, 50vw')}</div>
  <div class="split__text reveal"><span class="eyebrow">{t['cafe']}</span>
    <h2 id="cafe-title">{'Venez découvrir Café Zaytouna' if fr else 'Come discover Café Zaytouna'}</h2>
    <p>{'Un olivier dans le coin de la salle, des banquettes basses vertes aux motifs tissés, des tables en bois clair et une vitrine de pâtisseries au comptoir.' if fr else 'An olive tree in the corner, low green floor seating with woven patterns, light wood tables and a pastry display at the counter.'}</p>
    <p style="display:flex;flex-wrap:wrap;gap:.6rem"><a class="btn" href="{rel(cur, PAGES['cafe'][lang])}"><span>{'Découvrir le café' if fr else 'See the café'}</span>{ARROW}</a>
      <a class="btn btn--ghost" href="{rel(cur, PAGES['visit'][lang])}">{t['directions']}</a></p></div>
</div></section>

<section class="section reviews on-band" aria-labelledby="avis-title"><div class="wrap">
  <div class="reviews__grid">
    <div class="reveal"><span class="eyebrow">{'Avis Google' if fr else 'Google reviews'}</span>
      <h2 id="avis-title" class="sr">{'Note de nos clients' if fr else 'Our guests’ rating'}</h2>
      <div class="score"><span class="score__num">{f'{RATING:.1f}'.replace('.', ',') if fr else f'{RATING:.1f}'}</span>
        <div class="score__meta">{stars()}<span class="score__count">{('sur 5 · ' + str(REVIEW_COUNT) + ' avis Google') if fr else ('out of 5 · ' + str(REVIEW_COUNT) + ' Google reviews')}</span></div></div>
      <p class="lede">{'Merci à toutes les personnes qui ont partagé leur visite.' if fr else 'Thank you to everyone who shared their visit.'}</p>
      <p style="display:flex;flex-wrap:wrap;gap:.6rem"><a class="btn btn--light btn--lg" href="{rel(cur, PAGES['reviews'][lang])}"><span>{'Lire les avis' if fr else 'Read the reviews'}</span>{ARROW}</a>
        {btn(MAPS_URL, 'Google', 'btn btn--outline-light btn--lg', arrow=False)}</p></div>
    <div class="reviews__img reveal">{img(cur, 'duo-glaces', lang, '380px', alt='', large=False)}</div>
  </div>
  <div class="quotes-3">{q3}</div>
</div></section>

<section class="section" aria-labelledby="visit-title"><div class="wrap split split--rev">
  <div class="split__img reveal" style="aspect-ratio:4/5;max-width:460px">{img(cur, 'facade-soir', lang, '460px', large=False)}</div>
  <div class="split__text reveal"><span class="eyebrow">{t['visit']}</span>
    <h2 id="visit-title">{'Au 8762, rue Lajeunesse' if fr else 'At 8762 Rue Lajeunesse'}</h2>
    {open_status(lang)}
    {hours_table(lang)}
    <p><a class="tel" href="tel:{PHONE_E164}">{PHONE[lang]}</a></p>
    <p style="display:flex;flex-wrap:wrap;gap:.6rem"><a class="btn" href="{rel(cur, PAGES['visit'][lang])}"><span>{'Plan et itinéraire' if fr else 'Map and directions'}</span>{ARROW}</a></p></div>
</div></section>"""
    title = ("Café Zaytouna · Café, matcha et crème brûlée à Montréal" if fr else "Café Zaytouna · Coffee, matcha & crème brûlée in Montréal")
    desc = ("Café Zaytouna, 8762 rue Lajeunesse à Montréal : matchas, lattes crème brûlée, sandwichs et desserts. 4,9/5 sur Google. Commandez en ligne ou venez nous voir."
            if fr else "Café Zaytouna, 8762 Rue Lajeunesse in Montréal: matcha, crème brûlée lattes, sandwiches and desserts. Rated 4.9/5 on Google. Order online or visit us.")
    ld = [{"@type": "WebSite", "name": NAME, "url": SITE_URL + "/", "inLanguage": ["fr-CA", "en-CA"]}]
    return cur, layout(cur, "home", lang, title, desc, body, ld)

def page_menu(lang):
    cur = PAGES["menu"][lang]; t = T[lang]; fr = lang == "fr"
    trail = [(t["home"], PAGES["home"][lang]), (t["menu"], cur)]
    chips = "".join(f'<li><a href="#{c["id"]}">{c[lang]}</a></li>' for c in CATS)
    cats = ""
    for c in CATS:
        items = [i for i in ITEMS if i["cat"] == c["id"]]
        rows = "".join(f"""<li><a href="{item_link(cur, i, lang)}"><span class="board__name">{iname(i, lang)}</span><span class="price">{price(i['price'], lang)}</span>
          <span class="board__desc">{i['fr_d'] if fr else i['en_d']}{(' ' + t['nuts'] + '.') if i.get('nuts') else ''}</span></a></li>""" for i in items)
        photo = f'<div class="cat__photo">{img(cur, c["photo"], lang, "300px", large=False)}</div>' if c["photo"] else ""
        n = len(items)
        cnt = f"{n} {'choix' if fr else ('items' if n > 1 else 'item')}"
        cats += f"""<section class="cat" id="{c['id']}" aria-labelledby="h-{c['id']}"><div class="cat__grid">
  <div class="cat__head reveal"><span class="cat__count">{cnt}</span><h2 id="h-{c['id']}">{c[lang]}</h2><p>{c['fr_d'] if fr else c['en_d']}</p>{photo}</div>
  <ul class="board__list reveal">{rows}</ul></div></section>"""
    others = ("Sur place et sur Uber Eats, vous trouverez aussi le bar à espresso, les viennoiseries et nos classiques maison. Les prix peuvent changer; ils sont affichés sur Uber Eats en octobre 2026, avant taxes et frais."
              if fr else "In the café and on Uber Eats you'll also find our espresso bar, pastries and house classics. Prices are as listed on Uber Eats in October 2026, before taxes and fees, and may change.")
    body = f"""{crumbs_html(cur, trail, lang)}
<section class="page-hero"><div class="wrap page-hero__grid">
  <div class="hero__text"><span class="eyebrow">{NAME} · Montréal</span>
    <h1>{'Le menu' if fr else 'The menu'}</h1>
    <p class="lede">{'Matchas glacés, lattes signatures, limonades, sandwichs et crèmes brûlées. Choisissez un produit pour en savoir plus, ou commandez directement.' if fr else 'Iced matcha, signature lattes, lemonades, sandwiches and crème brûlée. Pick an item to learn more, or order directly.'}</p></div>
  <div class="page-hero__side">{btn(ORDER_URL, t['see_menu'], 'btn btn--lg')}<ul class="chips" aria-label="{t['category']}">{chips}</ul></div>
</div></section>
<div class="wrap">{cats}
  <div class="price-note reveal"><p>{others}</p>{btn(ORDER_URL, t['order'], 'btn btn--lg')}</div>
</div>
<section class="section"><div class="wrap">
  <div class="section__head reveal"><span class="eyebrow">{'Sur nos plateaux' if fr else 'On our trays'}</span>
    <h2>{'Tel que servi au café' if fr else 'As served in the café'}</h2></div>
  <div class="gallery">
    <figure class="g1 reveal"><div class="g-img">{img(cur, 'cheesecake', lang, '50vw', large=False)}</div></figure>
    <figure class="g2 reveal"><div class="g-img">{img(cur, 'plateau-limonades', lang, '50vw', large=False)}</div></figure>
    <figure class="g3 reveal"><div class="g-img">{img(cur, 'duo-glaces', lang, '33vw', large=False)}</div></figure>
    <figure class="g4 reveal"><div class="g-img">{img(cur, 'latte-creme-brulee', lang, '33vw', large=False)}</div></figure>
    <figure class="g5 reveal"><div class="g-img">{img(cur, 'matcha-creme-brulee', lang, '33vw', large=False)}</div></figure>
  </div>
</div></section>"""
    menu_ld = {"@type": "Menu", "name": f"{NAME} — {t['menu']}", "inLanguage": "fr-CA" if fr else "en-CA", "hasMenuSection": [
        {"@type": "MenuSection", "name": c[lang], "hasMenuItem": [
            {"@type": "MenuItem", "name": iname(i, lang), "description": i["fr_d"] if fr else i["en_d"], "url": absurl(PAGES["item:" + i["id"]][lang]),
             "offers": {"@type": "Offer", "price": f"{i['price']:.2f}", "priceCurrency": "CAD"}} for i in ITEMS if i["cat"] == c["id"]]} for c in CATS]}
    title = "Menu · Café Zaytouna Montréal — matchas, lattes, sandwichs" if fr else "Menu · Café Zaytouna Montréal — matcha, lattes, sandwiches"
    desc = ("Menu de Café Zaytouna, Montréal : matcha crème brûlée, matcha fraise, latte crème brûlée, wraps, sandwich poulet BBQ et crème brûlée. Prix et commande."
            if fr else "Café Zaytouna menu, Montréal: crème brûlée matcha, strawberry matcha, crème brûlée latte, wraps, BBQ chicken sandwich and crème brûlée. Prices and ordering.")
    return cur, layout(cur, "menu", lang, title, desc, body, [menu_ld, breadcrumb_ld(trail)], active="menu")

OLIVE_SVG = '<svg class="plate__olive" viewBox="0 0 64 64" aria-hidden="true"><path d="M14 50C22 30 36 18 54 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><ellipse cx="30" cy="22" rx="11" ry="5" transform="rotate(-40 30 22)" fill="currentColor" opacity=".55"/><ellipse cx="42" cy="30" rx="11" ry="5" transform="rotate(-10 42 30)" fill="currentColor" opacity=".4"/><ellipse cx="24" cy="44" rx="9" ry="11" fill="currentColor"/></svg>'

def page_item(i, lang):
    key = "item:" + i["id"]; cur = PAGES[key][lang]; t = T[lang]; fr = lang == "fr"
    c = CAT[i["cat"]]; nm = iname(i, lang)
    trail = [(t["home"], PAGES["home"][lang]), (t["menu"], PAGES["menu"][lang]), (nm, cur)]
    if i.get("photo"):
        visual = f'<div class="item__visual">{img(cur, i["photo"], lang, "(max-width: 960px) 80vw, 520px", eager=True)}</div>'
        og = {"matcha-creme-brulee": "og-matcha", "latte-creme-brulee": "og-latte"}[i["photo"]]
    else:
        visual = f"""<div class="item__visual plate" aria-hidden="true"><span class="plate__cat">{c[lang]}</span>
  <span class="plate__name">{nm}</span><div class="kilim"></div><span style="color:var(--band-soft)">{OLIVE_SVG}</span></div>"""
        og = "og-home"
    revs = reviews_for(i["id"])
    rev_html = ""
    if revs:
        rev_html = f"""<section class="section exp" aria-labelledby="rv-title"><div class="wrap">
  <div class="section__head reveal"><span class="eyebrow">{'Avis Google' if fr else 'Google reviews'}</span><h2 id="rv-title">{t['what_say']}</h2></div>
  <div class="quotes">{''.join(quote(r, lang) for r in revs)}</div>
  <p style="margin-top:1rem"><a class="link" href="{rel(cur, PAGES['reviews'][lang])}">{'Tous les avis' if fr else 'All reviews'}</a></p></div></section>"""
    sibs = [x for x in ITEMS if x["cat"] == i["cat"] and x["id"] != i["id"]]
    if len(sibs) < 2: sibs += [x for x in ITEMS if x.get("star") and x["id"] != i["id"] and x not in sibs][: 4 - len(sibs)]
    sibs = sibs[:4]
    rel_html = "".join(f'<a href="{item_link(cur, x, lang)}"><b>{iname(x, lang)}</b><span>{price(x["price"], lang)}</span></a>' for x in sibs)
    alt_name = "" if fr else f'<p class="fineprint">{"On our menu as" if not fr else ""} <span lang="fr">{i["name"]}</span></p>'
    body = f"""{crumbs_html(cur, trail, lang)}
<section class="item"><div class="wrap item__grid">
  {visual}
  <div class="item__info">
    <span class="eyebrow"><a href="{rel(cur, PAGES['menu'][lang])}#{c['id']}" style="text-decoration:none">{c[lang]}</a></span>
    <h1>{nm}</h1>{alt_name}
    <span class="item__price">{price(i['price'], lang)}</span>
    <p class="item__desc">{i['fr_d'] if fr else i['en_d']}</p>
    {f'<span class="allergen">{t["nuts"]}</span>' if i.get('nuts') else ''}
    <div class="item__ctas" id="hero-ctas">{btn(ORDER_URL, t['order'], 'btn btn--lg')}
      <a class="btn btn--ghost btn--lg" href="{rel(cur, PAGES['menu'][lang])}">{t['all_menu']}</a></div>
    <div class="item__facts"><span><strong>{NAME}</strong> · {t['addr_line']}</span>{open_status(lang)}
      <span>{t['price_note']}</span></div>
  </div>
</div></section>
{rev_html}
<section class="section" style="padding-top:clamp(48px,6vw,80px)"><div class="wrap">
  <h2 class="reveal" style="font-size:clamp(1.6rem,3vw,2.2rem);margin-bottom:1.4rem">{t['also'] if all(x['cat'] == i['cat'] for x in sibs) else ('À essayer aussi' if fr else 'Also worth trying')}</h2>
  <div class="related reveal">{rel_html}</div>
  <div class="visit-strip reveal" style="margin-top:clamp(32px,5vw,56px)">
    <dl><div><dt>{t['address']}</dt><dd>{t['addr_line']}</dd></div><div><dt>{t['phone']}</dt><dd><a class="tel" href="tel:{PHONE_E164}">{PHONE[lang]}</a></dd></div></dl>
    <a class="btn btn--ghost" href="{rel(cur, PAGES['visit'][lang])}">{t['directions']}</a></div>
</div></section>"""
    d = i["fr_d"] if fr else i["en_d"]
    title = f"{nm} · {price(i['price'], lang)} · Café Zaytouna Montréal"
    base = (f"{nm} à {price(i['price'], lang)} chez Café Zaytouna, 8762 rue Lajeunesse, Montréal. {d}" if fr
            else f"{nm}, {price(i['price'], lang)}, at Café Zaytouna, 8762 Rue Lajeunesse, Montréal. {d}")
    tail = " Commandez en ligne." if fr else " Order online."
    desc = fit(base + tail) if len(base + tail) <= 160 else fit(base)
    mi = {"@type": "MenuItem", "name": nm, "description": d, "url": absurl(cur),
          "offers": {"@type": "Offer", "price": f"{i['price']:.2f}", "priceCurrency": "CAD", "url": ORDER_URL}}
    if i.get("photo"): mi["image"] = SITE_URL + f"/assets/img/{i['photo']}-1100.webp"
    return cur, layout(cur, key, lang, title, desc, body, [mi, breadcrumb_ld(trail)], og_image=og, active="menu")

def page_cafe(lang):
    cur = PAGES["cafe"][lang]; t = T[lang]; fr = lang == "fr"
    trail = [(t["home"], PAGES["home"][lang]), (t["cafe"], cur)]
    q = "".join(quote(r, lang) for r in reviews_for("cafe"))
    check = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>'
    notes_fr = ["Banquettes au sol de style majlis, en tissu vert à motifs tissés", "Tables en bois clair et chaises vert olive", "Un olivier, des panneaux de bois à lattes et des miroirs arqués", "Une vitrine de gâteaux et pâtisseries au comptoir", "Une petite terrasse aux guirlandes lumineuses"]
    notes_en = ["Majlis-style floor seating in green woven fabric", "Light wood tables and olive-green chairs", "An olive tree, slatted wood panels and arched mirrors", "A display case of cakes and pastries at the counter", "A small terrace with string lights"]
    notes = "".join(f"<li>{check}<span>{n}</span></li>" for n in (notes_fr if fr else notes_en))
    body = f"""{crumbs_html(cur, trail, lang)}
<section class="page-hero"><div class="wrap page-hero__grid">
  <div class="hero__text"><span class="eyebrow">{'Ahuntsic · rue Lajeunesse' if fr else 'Ahuntsic · Rue Lajeunesse'}</span>
    <h1>{'Le café' if fr else 'The café'}</h1>
    <p class="lede">{'Un espace lumineux pour prendre son temps : au salon sur les banquettes basses, à une table près de la fenêtre ou en terrasse.' if fr else 'A bright space to take your time: in the lounge on low floor seating, at a table by the window or out on the terrace.'}</p></div>
  <div class="page-hero__side">{btn(rel(cur, PAGES['visit'][lang]), t['directions'], 'btn btn--lg', ext=False)}</div>
</div></section>
<div class="wrap"><div class="gallery">
  <figure class="g1 reveal"><div class="g-img">{img(cur, 'coin-salon', lang, '(max-width: 600px) 46vw, 50vw', eager=True)}</div><figcaption>{'Le coin salon et son olivier' if fr else 'The lounge corner and its olive tree'}</figcaption></figure>
  <figure class="g2 reveal"><div class="g-img">{img(cur, 'salle', lang, '(max-width: 600px) 46vw, 50vw', eager=True)}</div><figcaption>{'La salle' if fr else 'The dining room'}</figcaption></figure>
  <figure class="g3 reveal"><div class="g-img">{img(cur, 'comptoir', lang, '33vw', large=False)}</div><figcaption>{'Le comptoir' if fr else 'The counter'}</figcaption></figure>
  <figure class="g4 reveal"><div class="g-img">{img(cur, 'facade-soir', lang, '33vw', large=False)}</div><figcaption>{'La terrasse, le soir' if fr else 'The terrace at night'}</figcaption></figure>
  <figure class="g5 reveal"><div class="g-img">{img(cur, 'duo-glaces', lang, '33vw', large=False)}</div><figcaption>{'Au salon' if fr else 'In the lounge'}</figcaption></figure>
</div></div>
<section class="section"><div class="wrap split">
  <div class="split__text reveal"><span class="eyebrow">{'Dans le café' if fr else 'Inside'}</span>
    <h2>{'Les détails qui font Zaytouna' if fr else 'The details that make Zaytouna'}</h2>
    <ul class="notes">{notes}</ul></div>
  <div class="split__img reveal" style="aspect-ratio:3/4;max-width:460px;justify-self:end">{img(cur, 'matcha-creme-brulee', lang, '460px', large=False)}</div>
</div></section>
<section class="section exp"><div class="wrap">
  <div class="section__head reveal"><span class="eyebrow">{'Avis Google' if fr else 'Google reviews'}</span><h2>{'Ce que nos clients remarquent' if fr else 'What our guests notice'}</h2></div>
  <div class="quotes">{q}</div>
</div></section>"""
    title = "Le café · Café Zaytouna, coin salon et terrasse à Montréal" if fr else "The café · Café Zaytouna lounge and terrace in Montréal"
    desc = ("Découvrez Café Zaytouna : banquettes de style majlis, olivier, tables en bois et petite terrasse au 8762 rue Lajeunesse, Montréal."
            if fr else "Step inside Café Zaytouna: majlis-style floor seating, an olive tree, wood tables and a small terrace at 8762 Rue Lajeunesse, Montréal.")
    return cur, layout(cur, "cafe", lang, title, desc, body, [breadcrumb_ld(trail)], active="cafe")

def page_reviews(lang):
    cur = PAGES["reviews"][lang]; t = T[lang]; fr = lang == "fr"
    trail = [(t["home"], PAGES["home"][lang]), (t["reviews"], cur)]
    qs = "".join(quote(r, lang, "quote--lg" if n in (0, 7, 12) else "") for n, r in enumerate(REVIEWS))
    body = f"""{crumbs_html(cur, trail, lang)}
<section class="page-hero"><div class="wrap page-hero__grid">
  <div class="hero__text"><span class="eyebrow">{'Avis Google' if fr else 'Google reviews'}</span>
    <h1>{'Vos avis' if fr else 'Your reviews'}</h1>
    <p class="lede">{'Une sélection d’avis laissés sur notre fiche Google. Retrouvez-les tous, avec leurs photos, directement sur Google.' if fr else 'A selection of reviews left on our Google listing. See them all, with photos, directly on Google.'}</p></div>
  <div class="page-hero__side">
    <div class="score" style="margin:0"><span class="score__num" style="font-size:clamp(4.5rem,10vw,7rem)">{f'{RATING:.1f}'.replace('.', ',') if fr else f'{RATING:.1f}'}</span>
      <div class="score__meta">{stars()}<span class="score__count">{('sur 5 · ' + str(REVIEW_COUNT) + ' avis Google') if fr else ('out of 5 · ' + str(REVIEW_COUNT) + ' Google reviews')}</span></div></div>
    <p style="display:flex;flex-wrap:wrap;gap:.6rem">{btn(MAPS_URL, t['read_google'], 'btn')}{btn(REVIEW_URL, t['leave_review'], 'btn btn--ghost', arrow=False)}</p>
  </div>
</div></section>
<section class="section" style="padding-top:0"><div class="wrap"><p class="lang-note" style="margin-bottom:1.2rem">{'Les avis sont reproduits dans leur langue d’origine (anglais).' if fr else ''}</p>
  <div class="quotes">{qs}</div></div></section>"""
    title = f"Avis · Café Zaytouna Montréal — {rating_text('fr')}" if fr else f"Reviews · Café Zaytouna Montréal — {rating_text('en')}"
    desc = ("Ce que nos clients disent de Café Zaytouna à Montréal : matcha crème brûlée, latte crème brûlée, service et ambiance. Note de 4,9/5 sur Google."
            if fr else "What guests say about Café Zaytouna in Montréal: crème brûlée matcha, crème brûlée latte, service and atmosphere. Rated 4.9/5 on Google.")
    return cur, layout(cur, "reviews", lang, title, desc, body, [breadcrumb_ld(trail)], active="reviews")

def page_visit(lang):
    cur = PAGES["visit"][lang]; t = T[lang]; fr = lang == "fr"
    trail = [(t["home"], PAGES["home"][lang]), (t["visit"], cur)]
    metro = reviews_for("visit")[0]
    body = f"""{crumbs_html(cur, trail, lang)}
<section class="page-hero" style="padding-bottom:clamp(16px,3vw,32px)"><div class="wrap">
  <div class="hero__text"><span class="eyebrow">{t['visit_us']}</span>
    <h1>{'Nous trouver' if fr else 'Find us'}</h1>
    <p class="lede">{'8762, rue Lajeunesse, Montréal. Ouvert tous les jours.' if fr else '8762 Rue Lajeunesse, Montréal. Open every day.'}</p></div>
</div></section>
<section class="section" style="padding-top:clamp(16px,3vw,32px)"><div class="wrap visit__grid">
  <div class="visit__info reveal">
    <dl class="facts">
      <div><dt>{t['address']}</dt><dd><address style="font-style:normal">{t['addr_html']}</address></dd></div>
      <div><dt>{t['hours']}</dt><dd>{open_status(lang)}<div style="margin-top:.6rem">{hours_table(lang)}</div></dd></div>
      <div><dt>{t['phone']}</dt><dd><a class="tel link" href="tel:{PHONE_E164}">{PHONE[lang]}</a></dd></div>
      <div><dt>Instagram</dt><dd><a class="link" href="{INSTAGRAM}" target="_blank" rel="noopener">@cafezaytouna</a></dd></div>
    </dl>
    <p id="hero-ctas" style="display:flex;flex-wrap:wrap;gap:.6rem">{btn(MAPS_URL, t['directions'], 'btn btn--lg')}<a class="btn btn--ghost btn--lg" href="tel:{PHONE_E164}">{t['call']}</a></p>
  </div>
  <div class="map reveal" id="map">
    <div class="map__fallback"><strong>{NAME}</strong><span>{t['addr_line']}</span>
      <button class="btn" type="button" data-map-src="{E(MAP_EMBED)}" data-map-title="{E(('Carte Google' if fr else 'Google map') + ' : ' + NAME + ', ' + t['addr_line'])}">{t['show_map']}</button>
      <small class="map__note">{t['map_note']}</small>
      <a class="link" href="{MAPS_URL}" target="_blank" rel="noopener">{t['open_maps']}</a></div>
  </div>
</div></section>
<section class="section exp"><div class="wrap split">
  <div class="split__img reveal" style="aspect-ratio:3/4;max-width:460px">{img(cur, 'facade-soir', lang, '460px', large=False)}</div>
  <div class="split__text reveal"><span class="eyebrow">{'Repère' if fr else 'Look for'}</span>
    <h2>{'La vitrine au logo rond' if fr else 'The window with the round logo'}</h2>
    <p>{'Repérez notre vitrine et son logo à l’olivier, avec la petite terrasse juste à côté.' if fr else 'Look for our window with the olive-branch logo and the small terrace right beside it.'}</p>
    {quote(metro, lang)}</div>
</div></section>"""
    title = "Nous trouver · Café Zaytouna, 8762 rue Lajeunesse, Montréal — heures et itinéraire" if fr else "Find us · Café Zaytouna, 8762 Rue Lajeunesse, Montréal — hours and directions"
    desc = ("Adresse, heures d'ouverture, téléphone et itinéraire de Café Zaytouna : 8762 rue Lajeunesse, Montréal. Ouvert tous les jours, " + hours_txt(11, 20, 'fr') + " du lundi au jeudi."
            if fr else "Address, opening hours, phone and directions for Café Zaytouna: 8762 Rue Lajeunesse, Montréal. Open daily, " + hours_txt(11, 20, 'en') + " Monday to Thursday.")
    return cur, layout(cur, "visit", lang, title, desc, body, [breadcrumb_ld(trail)], active="visit")


def page_legal(kind, lang):
    cur = PAGES[kind][lang]; t = T[lang]; fr = lang == "fr"
    trail = [(t["home"], PAGES["home"][lang]), (t[kind], cur)]
    contact = {"addr": t["addr_line"] + (" (Québec) H2M 1R6" if fr else ", QC H2M 1R6"), "phone": PHONE[lang], "tel": PHONE_E164}
    sections = (legal.privacy if kind == "privacy" else legal.terms)(lang, contact)
    toc = "".join(f'<li><a href="#s{n+1}">{E(h)}</a></li>' for n, (h, _) in enumerate(sections))
    secs = "".join(f'<section id="s{n+1}" class="legal__sec"><h2>{E(h)}</h2>' + "".join(f"<p>{para}</p>" for para in paras) + "</section>"
                   for n, (h, paras) in enumerate(sections))
    body = f"""{crumbs_html(cur, trail, lang)}
<section class="page-hero"><div class="wrap">
  <div class="hero__text"><span class="eyebrow">{t['legal']}</span><h1>{t[kind]}</h1>
    <p class="lede">{t['updated']}{' :' if fr else ':'} {legal.UPDATED[lang]}</p></div>
</div></section>
<div class="wrap legal"><nav class="legal__toc" aria-label="{t[kind]}"><ol>{toc}</ol></nav><div class="legal__body">{secs}</div></div>"""
    if kind == "privacy":
        title = f"{t['privacy']} · {NAME}"
        desc = ("Comment Café Zaytouna traite les renseignements personnels : aucun témoin, aucun formulaire, services tiers et vos droits selon la Loi 25."
                if fr else "How Café Zaytouna handles personal information: no cookies, no forms, third-party services and your rights under Québec’s Law 25.")
    else:
        title = f"{t['terms']} · {NAME}"
        desc = ("Conditions d’utilisation du site de Café Zaytouna : information sur le menu et les prix, commandes en ligne, propriété intellectuelle et droit applicable."
                if fr else "Terms of use for the Café Zaytouna website: menu and price information, online ordering, intellectual property and governing law.")
    return cur, layout(cur, kind, lang, title, desc, body, [breadcrumb_ld(trail)])

def page_404():
    cur = "404.html"
    body = f"""<section class="page-hero"><div class="wrap">
  <div class="hero__text"><span class="eyebrow">404</span><h1>Page introuvable</h1>
    <p class="lede">Cette page n’existe pas ou a été déplacée. <span lang="en">This page doesn’t exist or has moved.</span></p>
    <div class="hero__ctas" id="hero-ctas"><a class="btn btn--lg" href="/index.html">Accueil</a><a class="btn btn--ghost btn--lg" href="/menu.html">Menu</a>
      <a class="btn btn--ghost btn--lg" href="/en/index.html" lang="en">English</a></div></div>
</div></section>"""
    head, html_body = layout(cur, "home", "fr", f"Page introuvable · {NAME}", "Page introuvable.", body, robots="noindex,follow")
    return head.replace(f'<link rel="canonical" href="{absurl("index.html")}">', ""), html_body

def min_css(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,>])\s*", r"\1", css)
    css = re.sub(r";}", "}", css)
    return css.strip()

def min_html(doc):
    return re.sub(r"\s*\n\s*", " ", doc).replace("> <head>", "><head>")

# Move inline style="" attributes into classes so the strict CSP (style-src 'self') holds.
UTIL = {}
TAG_RE = re.compile(r'<([a-zA-Z][\w-]*)((?:\s[^<>]*?)?)\sstyle="([^"]*)"([^<>]*)>')
def strip_styles(doc):
    def fix(m):
        tag, before, style, after = m.groups()
        cls = "u-" + hashlib.md5(style.encode()).hexdigest()[:6]
        UTIL[cls] = style
        attrs = before + after
        if re.search(r'\sclass="', attrs):
            attrs = re.sub(r'\sclass="([^"]*)"', lambda c: f' class="{c.group(1)} {cls}"', attrs, count=1)
        else:
            attrs += f' class="{cls}"'
        return f"<{tag}{attrs}>"
    prev = None
    while prev != doc:
        prev, doc = doc, TAG_RE.sub(fix, doc)
    return doc

def util_css():
    out = []
    for cls, style in sorted(UTIL.items()):
        decls = ";".join(d.strip() + " !important" for d in style.split(";") if d.strip())
        out.append(f".{cls}{{{decls}}}")
    return "\n/* moved from inline styles */\n" + "\n".join(out) + "\n"

# =========================== BUILD ===========================
HEADERS = {
  "Content-Security-Policy": CSP + "; frame-ancestors 'none'",
  "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=(), interest-cohort=(), browsing-topics=()",
  "Cross-Origin-Opener-Policy": "same-origin",
  "Cross-Origin-Resource-Policy": "same-origin",
  "X-Permitted-Cross-Domain-Policies": "none",
}

def write_host_configs():
    # Netlify & Cloudflare Pages
    lines = ["/*"] + [f"  {k}: {v}" for k, v in HEADERS.items()]
    lines += ["", "/assets/*", "  Cache-Control: public, max-age=31536000, immutable", "", "/*.html", "  Cache-Control: public, max-age=0, must-revalidate", ""]
    (OUT / "_headers").write_text("\n".join(lines), encoding="utf-8")
    # Vercel
    vercel = {"cleanUrls": False, "trailingSlash": False,
              "headers": [{"source": "/(.*)", "headers": [{"key": k, "value": v} for k, v in HEADERS.items()]},
                          {"source": "/assets/(.*)", "headers": [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}]}]}
    (OUT / "vercel.json").write_text(json.dumps(vercel, indent=2), encoding="utf-8")
    # Apache
    ht = ["# Café Zaytouna — security headers (Apache, needs mod_headers + mod_rewrite)", "Options -Indexes", "ServerSignature Off",
          "ErrorDocument 404 /404.html", "", "<IfModule mod_rewrite.c>", "  RewriteEngine On",
          "  RewriteCond %{HTTPS} !=on", "  RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]",
          "  RewriteRule (^|/)\\.(?!well-known/) - [F]", "</IfModule>", "", "<IfModule mod_headers.c>"]
    ht += [f'  Header always set {k} "{v}"' for k, v in HEADERS.items()]
    ht += ["  Header unset X-Powered-By", '  <FilesMatch "\\.(webp|jpg|png|ico|woff)$">', '    Header set Cache-Control "public, max-age=31536000, immutable"', "  </FilesMatch>", "</IfModule>",
           "", '<FilesMatch "\\.(py|md|txt|json|log|bak|sh)$">', "  Require all denied", "</FilesMatch>",
           '<FilesMatch "^(robots\\.txt|vercel\\.json)$">', "  Require all granted", "</FilesMatch>", ""]
    (OUT / ".htaccess").write_text("\n".join(ht), encoding="utf-8")
    # Nginx
    ng = ["# Café Zaytouna — add inside your server { } block", "server_tokens off;", "autoindex off;", "error_page 404 /404.html;",
          "location ~ /\\.(?!well-known) { deny all; }"]
    ng += [f"add_header {k} \"{v}\" always;" for k, v in HEADERS.items()]
    ng += ['location /assets/ { add_header Cache-Control "public, max-age=31536000, immutable" always;'] + [f"  add_header {k} \"{v}\" always;" for k, v in HEADERS.items()] + ["}"]
    (OUT / "nginx-security.conf").write_text("\n".join(ng) + "\n", encoding="utf-8")

def main():
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    pages = []
    for lang in ("fr", "en"):
        pages += [page_home(lang), page_menu(lang), page_cafe(lang), page_reviews(lang), page_visit(lang)]
        pages += [page_item(i, lang) for i in ITEMS]
        pages += [page_legal("privacy", lang), page_legal("terms", lang)]
    pages.append(("404.html", page_404()))
    for path, (head, body) in pages:
        lang = "en-CA" if path.startswith("en/") else "fr-CA"
        doc = (f'<!doctype html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n'
               f'<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n{head}\n</head>\n<body>\n{body}\n</body>\n</html>\n')
        if not PREVIEW: doc = min_html(strip_styles(doc))
        if path == "404.html":  # served at any URL, so make every local link absolute
            doc = re.sub(r'(href|src)="(?!https?:|/|#|tel:|data:|mailto:)', r'\1="/', doc)
            doc = re.sub(r'srcset="([^"]*)"', lambda m: 'srcset="' + re.sub(r'(^|, )(?!/)', r'\1/', m.group(1)) + '"', doc)
        p = OUT / path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(doc, encoding="utf-8")
        if PREVIEW and path == "index.html":  # artifact main page: content only, wrapped by the host
            (OUT / "_main.html").write_text(f"{head}\n{body}\n", encoding="utf-8")
    if not PREVIEW:
        shutil.copytree(ROOT / "assets", OUT / "assets")
        (OUT / "styles.css").write_text(min_css(CSS + util_css()), encoding="utf-8")
        shutil.copy(ROOT / "assets/favicon.ico", OUT / "favicon.ico")
        (OUT / "site.webmanifest").write_text(json.dumps({"name": NAME, "short_name": "Zaytouna", "lang": "fr-CA", "start_url": "/index.html",
            "display": "browser", "background_color": "#F5F6F0", "theme_color": "#183F1B",
            "icons": [{"src": "/assets/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "/assets/icon-512.png", "sizes": "512x512", "type": "image/png"}]},
            ensure_ascii=False, indent=2), encoding="utf-8")
        write_host_configs()
        (OUT / "site.js").write_text(JS, encoding="utf-8")
        urls = []; today = datetime.date.today().isoformat()
        for key, langs in PAGES.items():
            alts = "".join(f'<xhtml:link rel="alternate" hreflang="{h}" href="{absurl(langs[l])}"/>' for h, l in (("fr-CA", "fr"), ("en-CA", "en"), ("x-default", "fr")))
            imgs = sorted(set(re.findall(r'assets/img/([a-z-]+?)-1100\.webp', (OUT / langs["fr"]).read_text(encoding="utf-8"))))
            imgx = "".join(f"<image:image><image:loc>{SITE_URL}/assets/img/{n}-1100.webp</image:loc></image:image>" for n in imgs)
            pri = "1.0" if key == "home" else ("0.9" if key in ("menu", "visit") else ("0.3" if key in ("privacy", "terms") else "0.7"))
            for l in ("fr", "en"):
                urls.append(f"<url><loc>{absurl(langs[l])}</loc><lastmod>{today}</lastmod><priority>{pri}</priority>{alts}{imgx}</url>")
        (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
                                         + "\n".join(urls) + "\n</urlset>\n", encoding="utf-8")
        (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")
    print(f"{len(pages)} pages → {OUT}  (site URL: {SITE_URL})")

if __name__ == "__main__":
    main()
