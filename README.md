# Café Zaytouna website — start here

```
cafe-zaytouna/
├── (repo root)     ← the website itself (45 pages + images + vercel.json)
├── _source/         ← editable source: change content, then rebuild
├── _server-config/  ← only if your host uses Nginx
├── README.md        ← this file
└── SECURITY.md      ← security details and your account checklist
```

## Pages (French by default, full English version)
| | French | English |
|---|---|---|
| Home | `index.html` | `en/index.html` |
| Menu | `menu.html` | `en/menu.html` |
| 15 dish pages | `menu/matcha-creme-brulee-glace.html` … | `en/menu/iced-creme-brulee-matcha.html` … |
| The café | `le-cafe.html` | `en/the-cafe.html` |
| Reviews | `avis.html` | `en/reviews.html` |
| Hours & directions | `nous-trouver.html` | `en/find-us.html` |
| Privacy policy | `politique-de-confidentialite.html` | `en/privacy-policy.html` |
| Terms of use | `conditions-utilisation.html` | `en/terms-of-use.html` |
| Not-found page | `404.html` | (bilingual) |

Every page has a **FR | EN** switch in the header (and in the mobile menu) that opens the same page in the other language.

## SEO included
- Unique title and meta description (≤160 characters) on every page, one H1 per page, image alt text everywhere.
- Canonical URLs, French/English `hreflang` pairs, Open Graph and Twitter cards with 1200×630 share images.
- Structured data: CafeOrCoffeeShop (address, GPS, phone, hours, menu, order action), Menu, MenuItem with price, BreadcrumbList.
- `sitemap.xml` with hreflang and images, `robots.txt`, favicon, app icons, web manifest.
- Fast: self-hosted fonts (41 KB), WebP images with responsive sizes, lazy loading, no third-party scripts.

## Put it online on Vercel (cafe-zaytouna.vercel.app)
The pages are already set to **https://cafe-zaytouna.vercel.app** (canonical links, sitemap, share images, Google data).
1. Unzip. Go to vercel.com → **Add New → Project**. Either upload with the Vercel CLI (`cd site` then `npx vercel --prod`) or put the contents of the `site` folder in a GitHub repo and import it. Framework preset: **Other**, no build command, output directory: the folder root.
2. In the project's **Settings → Domains**, make sure the project is called `cafe-zaytouna` so the address is `cafe-zaytouna.vercel.app`. If that name is taken, tell me the address Vercel gives you and I'll rebuild with it.
3. `vercel.json` in the `site` folder applies all security headers automatically.
4. Google Search Console → add `https://cafe-zaytouna.vercel.app` (URL-prefix property, verify with the HTML-tag method — send me the tag and I'll add it) → submit `https://cafe-zaytouna.vercel.app/sitemap.xml`.
5. Google Business Profile and Instagram bio → set the website to `https://cafe-zaytouna.vercel.app`.
6. Do the account checklist in `SECURITY.md` (2FA everywhere).

If you later buy your own domain (e.g. cafezaytouna.com): run `python3 build.py https://www.your-domain.com` in `source/` and upload `source/dist/`.

## Change content later
Everything is in the DATA section at the top of `source/build.py`: hours, phone, rating, menu items and prices, reviews. Legal text is in `source/legal.py`. Edit, run `python3 build.py`, upload `source/dist/`.

## Sources and what to confirm
- Hours and phone: from the owner. Prices: the café's Uber Eats page, October 2026 (15 items listed there). Send the in-café menu to add espresso drinks, pastries and house classics.
- Dish descriptions only say what the name and photos show; have the café review them.
- 2 dishes have real photos; the 13 others show a branded name panel until photos are added (`photo="file-name"` in `build.py`).
- Reviews: Google reviews supplied by the owner, in their original English.
- Privacy policy and terms are written for a Québec café with this exact setup (no cookies, no forms). They are plain-language templates, not legal advice; a lawyer can review them. The person in charge of personal information is listed as "the owner" with the café phone. You can add a name and email in `source/legal.py`.
