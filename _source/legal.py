"""Privacy policy and terms of use (French and English). Plain-language, Québec-law oriented.
Have a lawyer review before launch if you need formal legal advice."""

UPDATED = {"fr": "8 octobre 2026", "en": "October 8, 2026"}

def privacy(lang, c):
    """c: dict of contact values (addr, phone, tel, links)."""
    if lang == "fr":
        return [
          ("Qui sommes-nous", [
            f"Café Zaytouna est un café situé au {c['addr']}. Cette politique explique comment nous traitons les renseignements personnels en lien avec ce site web, conformément à la <em>Loi sur la protection des renseignements personnels dans le secteur privé</em> du Québec (Loi 25)."]),
          ("Ce que ce site recueille", [
            "Ce site ne comporte <strong>aucun formulaire, compte client, infolettre, outil de statistiques ni publicité</strong>. Nous ne recueillons aucun renseignement personnel par l’intermédiaire du site.",
            "Le site n’utilise <strong>aucun témoin (cookie)</strong> ni technologie de suivi. Les polices de caractères et les images sont hébergées sur notre propre site : votre navigateur ne contacte aucun service tiers en consultant nos pages."]),
          ("Journaux techniques de l’hébergeur", [
            "Comme tout site web, notre hébergeur peut enregistrer automatiquement des données techniques lors de votre visite (adresse IP, type de navigateur, page demandée, date et heure). Ces données servent uniquement à assurer la sécurité et le bon fonctionnement du site, sont conservées pour une durée limitée selon les pratiques de l’hébergeur et ne sont pas utilisées pour vous identifier."]),
          ("Services de tiers", [
            f"<strong>Google Maps.</strong> Sur la page « Nous trouver », la carte ne se charge que si vous cliquez sur « Afficher la carte ». Google peut alors recueillir des données selon sa <a href=\"https://policies.google.com/privacy?hl=fr\" rel=\"noopener\" target=\"_blank\">politique de confidentialité</a>. Le bouton « Obtenir l’itinéraire » ouvre Google Maps dans un nouvel onglet.",
            "<strong>Commandes en ligne.</strong> Les boutons « Commander » mènent à Uber Eats. Votre commande et votre paiement sont traités par Uber selon sa <a href=\"https://www.uber.com/legal/fr/document/?name=privacy-notice&amp;country=canada&amp;lang=fr-ca\" rel=\"noopener\" target=\"_blank\">politique de confidentialité</a>. Nous ne recevons aucune donnée de paiement.",
            "<strong>Laisser un avis.</strong> Ce bouton mène à une page hébergée séparément (cafe-zaytouna-review.vercel.app). Les renseignements que vous y fournissez sont traités selon les modalités indiquées sur cette page.",
            "<strong>Instagram.</strong> Le lien vers @cafezaytouna ouvre Instagram, exploité par Meta selon sa propre politique de confidentialité."]),
          ("Avis Google reproduits", [
            "La page « Avis » reproduit des avis publiés publiquement sur notre fiche Google, avec le nom affiché par leur auteur sur Google. Si vous êtes l’auteur d’un avis et souhaitez qu’il soit retiré de notre site, contactez-nous : nous le retirerons rapidement."]),
          ("Si vous communiquez avec nous", [
            f"Si vous nous appelez au {c['phone']} ou nous écrivez sur Instagram, nous utilisons vos renseignements uniquement pour vous répondre et ne les communiquons à personne."]),
          ("Vos droits", [
            "Vous pouvez demander l’accès aux renseignements personnels que nous détenons à votre sujet, leur rectification ou leur suppression, et retirer votre consentement. Nous répondons dans un délai de 30 jours.",
            "Vous pouvez aussi porter plainte auprès de la <a href=\"https://www.cai.gouv.qc.ca\" rel=\"noopener\" target=\"_blank\">Commission d’accès à l’information du Québec</a>."]),
          ("Responsable de la protection des renseignements personnels", [
            f"La personne responsable est le propriétaire de Café Zaytouna. Joignez-le au <a href=\"tel:{c['tel']}\">{c['phone']}</a> ou en personne au {c['addr']}."]),
          ("Sécurité", [
            "Ce site est un site statique : il n’a ni base de données, ni espace d’administration accessible en ligne, ni code exécuté sur le serveur. Il est servi en HTTPS avec des en-têtes de sécurité stricts qui limitent les contenus autorisés."]),
          ("Modifications", [
            "Nous pouvons mettre à jour cette politique. La date de la dernière mise à jour figure en haut de la page."]),
        ]
    return [
      ("Who we are", [
        f"Café Zaytouna is a café located at {c['addr']}. This policy explains how we handle personal information in connection with this website, in line with Québec’s <em>Act respecting the protection of personal information in the private sector</em> (Law 25)."]),
      ("What this site collects", [
        "This site has <strong>no forms, customer accounts, newsletter, analytics or advertising</strong>. We do not collect any personal information through the site.",
        "The site uses <strong>no cookies</strong> and no tracking technology. Fonts and images are hosted on our own site, so your browser does not contact any third-party service when you view our pages."]),
      ("Hosting provider logs", [
        "Like any website, our hosting provider may automatically log technical data when you visit (IP address, browser type, requested page, date and time). This data is used only to keep the site secure and working, is kept for a limited time under the provider’s practices, and is not used to identify you."]),
      ("Third-party services", [
        "<strong>Google Maps.</strong> On the “Find us” page, the map only loads if you click “Show the map”. Google may then collect data under its <a href=\"https://policies.google.com/privacy?hl=en\" rel=\"noopener\" target=\"_blank\">privacy policy</a>. The “Get directions” button opens Google Maps in a new tab.",
        "<strong>Online ordering.</strong> “Order” buttons lead to Uber Eats. Your order and payment are handled by Uber under its <a href=\"https://www.uber.com/legal/en/document/?name=privacy-notice&amp;country=canada&amp;lang=en-ca\" rel=\"noopener\" target=\"_blank\">privacy notice</a>. We never receive payment data.",
        "<strong>Leave a review.</strong> This button leads to a separately hosted page (cafe-zaytouna-review.vercel.app). Information you provide there is handled under the terms shown on that page.",
        "<strong>Instagram.</strong> The @cafezaytouna link opens Instagram, operated by Meta under its own privacy policy."]),
      ("Google reviews shown on this site", [
        "Our “Reviews” page reproduces reviews posted publicly on our Google listing, with the name each author displays on Google. If you wrote a review and want it removed from our site, contact us and we will remove it promptly."]),
      ("If you contact us", [
        f"If you call us at {c['phone']} or message us on Instagram, we use your information only to reply and never share it."]),
      ("Your rights", [
        "You can ask to access, correct or delete the personal information we hold about you, and withdraw your consent. We reply within 30 days.",
        "You can also file a complaint with the <a href=\"https://www.cai.gouv.qc.ca\" rel=\"noopener\" target=\"_blank\">Commission d’accès à l’information du Québec</a>."]),
      ("Person in charge of personal information", [
        f"The person in charge is the owner of Café Zaytouna. Reach them at <a href=\"tel:{c['tel']}\">{c['phone']}</a> or in person at {c['addr']}."]),
      ("Security", [
        "This is a static website: it has no database, no online admin area and no code running on the server. It is served over HTTPS with strict security headers that limit what content can load."]),
      ("Changes", [
        "We may update this policy. The date of the latest update appears at the top of the page."]),
    ]

def terms(lang, c):
    if lang == "fr":
        return [
          ("Acceptation", ["En utilisant ce site, vous acceptez les présentes conditions. Si vous ne les acceptez pas, veuillez ne pas utiliser le site."]),
          ("Information sur le site", [
            "Le menu, les prix, les descriptions et les heures d’ouverture sont fournis à titre indicatif. Les prix proviennent de notre page Uber Eats, avant taxes et frais, et peuvent changer. En cas d’écart, les prix et heures affichés au café prévalent.",
            "<strong>Allergies :</strong> les mentions d’allergènes sur ce site ne sont pas exhaustives. Si vous avez une allergie ou une restriction alimentaire, parlez-en à notre équipe avant de commander."]),
          ("Commandes en ligne", ["Les commandes passées par Uber Eats sont régies par les conditions d’Uber. Aucune commande ni aucun paiement n’est traité sur ce site."]),
          ("Propriété intellectuelle", [
            "Le nom Café Zaytouna, son logo, les photographies et les textes de ce site appartiennent à Café Zaytouna. Toute reproduction sans autorisation écrite est interdite.",
            "Les avis reproduits appartiennent à leurs auteurs. Les polices Marcellus et Figtree sont utilisées sous licence SIL Open Font License."]),
          ("Liens externes", ["Le site contient des liens vers des services tiers (Uber Eats, Google, Instagram, page d’avis). Nous ne sommes pas responsables de leur contenu ni de leurs pratiques."]),
          ("Utilisation acceptable", ["Vous vous engagez à ne pas tenter de perturber le site, d’y accéder sans autorisation, d’en tester les failles sans permission, ni d’en copier le contenu de façon automatisée."]),
          ("Responsabilité", ["Dans la mesure permise par la loi, Café Zaytouna n’est pas responsable des dommages découlant de l’utilisation du site ou de son indisponibilité. Rien dans ces conditions ne limite les droits que vous accorde la <em>Loi sur la protection du consommateur</em> du Québec."]),
          ("Droit applicable", ["Ces conditions sont régies par les lois du Québec et les lois du Canada qui s’y appliquent. Tout litige relève des tribunaux du district judiciaire de Montréal."]),
          ("Modifications", ["Nous pouvons modifier ces conditions. La version en vigueur est celle publiée sur cette page."]),
          ("Nous joindre", [f"Café Zaytouna, {c['addr']} · <a href=\"tel:{c['tel']}\">{c['phone']}</a>"]),
        ]
    return [
      ("Acceptance", ["By using this site, you accept these terms. If you do not accept them, please do not use the site."]),
      ("Information on this site", [
        "The menu, prices, descriptions and opening hours are provided for information only. Prices come from our Uber Eats page, before taxes and fees, and may change. If anything differs, the prices and hours shown in the café apply.",
        "<strong>Allergies:</strong> allergen notes on this site are not exhaustive. If you have an allergy or dietary restriction, talk to our team before ordering."]),
      ("Online ordering", ["Orders placed through Uber Eats are governed by Uber’s terms. No orders or payments are processed on this site."]),
      ("Intellectual property", [
        "The Café Zaytouna name, logo, photographs and text on this site belong to Café Zaytouna. Reproduction without written permission is prohibited.",
        "Reviews shown belong to their authors. The Marcellus and Figtree fonts are used under the SIL Open Font License."]),
      ("External links", ["This site links to third-party services (Uber Eats, Google, Instagram, review page). We are not responsible for their content or practices."]),
      ("Acceptable use", ["You agree not to try to disrupt the site, access it without authorization, probe it for vulnerabilities without permission, or copy its content by automated means."]),
      ("Liability", ["To the extent permitted by law, Café Zaytouna is not liable for damages arising from use of the site or its unavailability. Nothing in these terms limits your rights under Québec’s <em>Consumer Protection Act</em>."]),
      ("Governing law", ["These terms are governed by the laws of Québec and the applicable laws of Canada. Any dispute falls under the courts of the judicial district of Montréal."]),
      ("Changes", ["We may change these terms. The version in force is the one published on this page."]),
      ("Contact", [f"Café Zaytouna, {c['addr']} · <a href=\"tel:{c['tel']}\">{c['phone']}</a>"]),
    ]
