#!/usr/bin/env python3
"""Fill empty locale bodies with translated definitions."""
import io, os, sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GLOSSARY_DIR = "website/src/content/glossary"

# Translations for 9 terms × 3 locales
TRANSLATIONS: dict[str, dict[str, str]] = {
    "access-control": {
        "nl": "## Definitie\n\nToegangsbeheer dwingt machtigingen af voor gebruikers, diensten en processen, zodat alleen geautoriseerde partijen bepaalde bronnen kunnen lezen of wijzigen.",
        "fr": "## Définition\n\nLe contrôle d'accès applique des autorisations pour les utilisateurs, les services et les processus, garantissant que seules les parties autorisées peuvent lire ou modifier des ressources spécifiques.",
        "de": "## Definition\n\nZugriffskontrolle setzt Berechtigungen für Benutzer, Dienste und Prozesse durch und stellt sicher, dass nur autorisierte Parteien bestimmte Ressourcen lesen oder ändern können.",
    },
    "audit-trail": {
        "nl": "## Definitie\n\nEen audittrail is een chronologisch logboek dat toont wie wat heeft gedaan en wanneer in een AI-systeem, ter ondersteuning van onderzoeken, compliance en verantwoording.",
        "fr": "## Définition\n\nUne piste d'audit est un journal chronologique qui montre qui a fait quoi et quand dans un système d'IA, facilitant les enquêtes, la conformité et la responsabilité.",
        "de": "## Definition\n\nEin Audit-Trail ist ein chronologisches Protokoll, das zeigt, wer was und wann in einem KI-System getan hat, und Untersuchungen, Compliance und Rechenschaftspflicht unterstützt.",
    },
    "data-governance": {
        "nl": "## Definitie\n\nData governance definieert hoe gegevens worden verzameld, gedocumenteerd, beschermd en gebruikt, in overeenstemming met juridische en organisatorische vereisten.",
        "fr": "## Définition\n\nLa gouvernance des données définit comment les données sont collectées, documentées, protégées et utilisées, en alignant les pratiques techniques avec les exigences juridiques et organisationnelles.",
        "de": "## Definition\n\nData Governance legt fest, wie Daten erhoben, dokumentiert, geschützt und genutzt werden, und bringt technische Praktiken mit rechtlichen und organisatorischen Anforderungen in Einklang.",
    },
    "data-residency": {
        "nl": "## Definitie\n\nVereisten voor dataresidentie specificeren in welke rechtsgebieden gegevens moeten worden opgeslagen of verwerkt, wat invloed heeft op cloud-, hosting- en leverancierskeuzes voor AI-systemen.",
        "fr": "## Définition\n\nLes exigences de résidence des données précisent dans quelles juridictions les données doivent être stockées ou traitées, influençant les choix de cloud, d'hébergement et de fournisseurs pour les systèmes d'IA.",
        "de": "## Definition\n\nAnforderungen an den Datenspeicherort legen fest, in welchen Rechtsgebieten Daten gespeichert oder verarbeitet werden müssen, und beeinflussen Cloud-, Hosting- und Anbieterwahl für KI-Systeme.",
    },
    "data-retention-policy": {
        "nl": "## Definitie\n\nEen beleid voor gegevensbewaring stelt minimale en maximale bewaartermijnen vast voor logbestanden, trainingsgegevens en gebruikersinhoud in overeenstemming met juridische en zakelijke vereisten.",
        "fr": "## Définition\n\nUne politique de conservation des données fixe les durées minimales et maximales de conservation des journaux, des données d'entraînement et du contenu utilisateur conformément aux exigences juridiques et commerciales.",
        "de": "## Definition\n\nEine Datenaufbewahrungsrichtlinie legt Mindest- und Höchstaufbewahrungsfristen für Protokolle, Trainingsdaten und Benutzerinhalte gemäß rechtlicher und geschäftlicher Anforderungen fest.",
    },
    "model-interpretability": {
        "nl": "## Definitie\n\nModelinterpreteerbaarheid betreft hoe gemakkelijk het gedrag van een model kan worden uitgelegd en geïnspecteerd, wat belangrijk is voor regelgevend en ethisch toezicht.",
        "fr": "## Définition\n\nL'interprétabilité d'un modèle concerne la facilité avec laquelle le comportement d'un modèle peut être expliqué et inspecté, ce qui est important pour le contrôle réglementaire et éthique.",
        "de": "## Definition\n\nModellinterpretierbarkeit betrifft, wie leicht das Verhalten eines Modells erklärt und überprüft werden kann, was für regulatorische und ethische Prüfungen wichtig ist.",
    },
    "privacy-by-design": {
        "nl": "## Definitie\n\nPrivacy by design betekent het inbedden van privacywaarborgen — zoals minimalisatie, toegangsbeheer en transparantie — in architecturen en processen, in plaats van ze als bijzaak te behandelen.",
        "fr": "## Définition\n\nLa protection de la vie privée dès la conception consiste à intégrer des mesures de protection — telles que la minimisation, le contrôle d'accès et la transparence — dans les architectures et les processus plutôt que de les traiter après coup.",
        "de": "## Definition\n\nPrivacy by Design bedeutet, Datenschutzmaßnahmen — wie Minimierung, Zugriffskontrolle und Transparenz — in Architekturen und Prozesse einzubetten, anstatt sie als nachträgliche Ergänzung zu behandeln.",
    },
    "role-based-access-control": {
        "nl": "## Definitie\n\nRolgebaseerd toegangsbeheer verleent of weigert toegang op basis van de rol van een gebruiker — zoals beheerder, reviewer of viewer — wat het beheer van machtigingen in complexe AI-systemen vereenvoudigt.",
        "fr": "## Définition\n\nLe contrôle d'accès basé sur les rôles accorde ou refuse l'accès en fonction du rôle d'un utilisateur — tel qu'administrateur, réviseur ou lecteur — simplifiant la gestion des autorisations dans les systèmes d'IA complexes.",
        "de": "## Definition\n\nRollenbasierte Zugriffskontrolle gewährt oder verweigert Zugriff basierend auf der Rolle eines Benutzers — wie Administrator, Prüfer oder Betrachter — und vereinfacht die Berechtigungsverwaltung in komplexen KI-Systemen.",
    },
    "source-provenance": {
        "nl": "## Definitie\n\nBronherkomst legt de oorsprong, het eigendom en de transformatiegeschiedenis van gegevens of inhoud vast, zodat de betrouwbaarheid en compliance ervan kunnen worden beoordeeld.",
        "fr": "## Définition\n\nLa provenance des sources enregistre l'origine, la propriété et l'historique de transformation des données ou du contenu afin que leur fiabilité et leur conformité puissent être évaluées.",
        "de": "## Definition\n\nQuellenherkunft dokumentiert den Ursprung, die Eigentumsverhältnisse und die Transformationshistorie von Daten oder Inhalten, damit deren Zuverlässigkeit und Compliance bewertet werden können.",
    },
}

updated = 0
for slug, locales in TRANSLATIONS.items():
    for loc, body_text in locales.items():
        fpath = os.path.join(GLOSSARY_DIR, f"{slug}-{loc}.mdx")
        if not os.path.exists(fpath):
            print(f"  Missing: {slug}-{loc}.mdx")
            continue

        with open(fpath, encoding="utf-8") as f:
            content = f.read()

        # Split at end of frontmatter
        parts = content.split("---", 2)
        if len(parts) < 3:
            print(f"  Bad frontmatter: {slug}-{loc}.mdx")
            continue

        existing_body = parts[2].strip()
        if len(existing_body) > 20:
            # Already has content, skip
            continue

        # Rebuild file: frontmatter + body
        new_content = parts[0] + "---" + parts[1] + "---\n\n" + body_text + "\n"

        # Preserve references if any
        if "## References" in content:
            refs_idx = content.find("## References")
            refs = content[refs_idx:]
            new_content = new_content.rstrip() + "\n\n" + refs.strip() + "\n"

        with open(fpath, "w", encoding="utf-8") as f:
            f.write(new_content)
        updated += 1

print(f"Updated: {updated} files")
