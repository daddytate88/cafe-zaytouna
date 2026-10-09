# Security — Café Zaytouna website

## Why there is no "backend" to hack
This site is **static**: plain HTML, CSS, JavaScript and images. There is:
- no database, no admin login, no customer accounts, no forms, no server code;
- no payments (orders go to Uber Eats, which handles payment security);
- no cookies, no analytics, no third-party scripts or fonts.

Most website hacks target exactly those pieces (logins, databases, plugins like on WordPress). Here they don't exist, so the attack surface is about as small as a website can have. No website can honestly be called "100 % unhackable", but this setup removes the usual ways in.

## Protections built into the files
- **Content-Security-Policy**: the browser only runs scripts, styles, fonts and images from your own domain. Injected code from anywhere else is blocked. The only outside frame allowed is the Google map, and it loads only after a visitor clicks "Afficher la carte".
- **HTTPS forced** with HSTS (2 years), plus `X-Frame-Options: DENY` and `frame-ancestors 'none'` (no one can embed your site to trick visitors), `nosniff`, a strict referrer policy, camera/mic/location/payment disabled, and cross-origin isolation.
- Ready-made configs for every common host:
  - `site/_headers` → Netlify and Cloudflare Pages (picked up automatically)
  - `site/vercel.json` → Vercel (picked up automatically)
  - `site/.htaccess` → Apache shared hosting (also forces HTTPS, blocks hidden files, disables folder listing)
  - `server-config/nginx-security.conf` → Nginx servers
- All external links use `rel="noopener"`.
- Tested: all 45 pages load under the full policy with zero blocked content and zero requests to outside servers.

## What YOU must protect (this is where real risk is)
1. **Hosting account** (Netlify / Vercel / Cloudflare / other): strong unique password + **two-factor authentication (2FA)**.
2. **Vercel account**: 2FA on, and only invite people who need access. (If you later buy your own domain, turn on 2FA and transfer lock at the registrar too.)
3. **Email account** linked to those two: 2FA. Whoever controls this email can reset everything else.
4. **Google Business Profile, Uber Eats and Instagram**: 2FA on each. These are what customers actually see.
5. Only give access to people who need it; remove ex-staff.

## After launch — 5-minute check
- Visit https://securityheaders.com and enter `cafe-zaytouna.vercel.app` → you should get **A** or **A+**.
- Visit https://www.ssllabs.com/ssltest/ → should be **A** or better.

## Optional extra
Add a `.well-known/security.txt` file with a contact email so people can report problems responsibly (needs an email address — none was provided).
