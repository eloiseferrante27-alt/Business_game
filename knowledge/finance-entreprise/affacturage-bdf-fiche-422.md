# Affacturage (Banque de France, fiche 422)

> Source : Banque de France, « Le référentiel des financements des entreprises », chapitre 4, fiche 422 « L'affacturage », 05/2022 (la fiche reprend un extrait du site de l'ASF et cite Vernimmen, Finance d'entreprise 2021) : https://www.banque-france.fr/system/files/2024-04/823415%20Fiche-422.pdf (fichier mis en ligne en avril 2024). Consulté le 2026-11-24.
> Licence : publication de la Banque de France ; synthèse rédigée en interne, citations courtes. Droits de diffusion extérieure à confirmer.

## Définition

« L'affacturage (ou factoring) est une opération ou technique de gestion financière : une société spécialisée (le factor ou affactureur en français) prend en charge le recouvrement de créances d'une entreprise dans le cadre d'un contrat en supportant, de manière optionnelle, les pertes éventuelles sur les débiteurs insolvables. » Il permet d'améliorer la trésorerie « en transformant un actif dormant, les factures, en liquidités immédiates ».

L'affacturage classique recouvre trois prestations : le recouvrement du poste clients (enregistrement, relance, encaissement), le financement des créances cédées et l'assurance-crédit. Les sociétés d'affacturage sont agréées par l'ACPR comme établissement de crédit spécialisé ou société de financement.

## Paramètres chiffrés du contrat (fiche 422, 05/2022)

| Élément | Valeur dans la fiche |
|---|---|
| Montant avancé | généralement entre 85 et 95 % des créances cédées |
| Retenue de garantie | entre 8 et 15 % du montant des créances cédées, restituée à l'expiration du contrat |
| Commission d'affacturage (recouvrement, assurance éventuelle) | entre 0,2 % et 2 % du montant TTC des factures cédées |
| Commission de financement | indice du marché monétaire (EONIA/€STR ou EURIBOR 3 mois) majoré d'un pourcentage pouvant aller jusqu'à 2,5 % |

- La commission d'affacturage se prélève à chaque cession de créances ; son niveau dépend notamment des risques sur la clientèle, des impayés, de la dispersion géographique et du « délai moyen des crédits inter-entreprises accordés ».
- Le droit de recours du factor contre son client peut être exercé ou non (contrepassation des créances après l'échéance).
- Ces fourchettes datent de 2022 : le niveau de l'indice (EURIBOR, €STR) en 2026 n'est pas dans la fiche. Le `factoring_fee_rate` du jeu (commission et financement) est à calibrer à partir de ces ordres de grandeur, avec leur date.

## Marché (fiche 422)

- Le marché français représente près de 365 milliards d'euros de créances financées en 2021 (source ASF citée).
- La fiche rappelle le plafonnement des délais de règlement par la loi de modernisation de l'économie : « 60 jours nets à compter de la date d'émission de la facture ou 45 jours fin de mois » (en vigueur depuis le 1er janvier 2009) ; voir code-commerce-l441-10-d441-5-delais-paiement.md pour le texte actuel.
