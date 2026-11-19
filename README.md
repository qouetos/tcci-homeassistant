# TCCI : agenda du sommeil pour Home Assistant

Intégration Home Assistant pour **TCCI**, un boîtier ESP32 à 2 boutons posé à côté du lit, qui tient l'agenda du sommeil d'une thérapie TCC-I (insomnie). Elle fonctionne avec le boîtier en local (`http://tcci.local`) ou avec le serveur cloud TCCI.

## Installation

**HACS** : HACS → ⋮ → Dépôts personnalisés → `https://github.com/qouetos/tcci-homeassistant`, catégorie **Intégration** → Télécharger, puis redémarrer Home Assistant.

**Manuel** : copier `custom_components/tcci/` dans `/config/custom_components/tcci/`, puis redémarrer.

Ensuite : *Paramètres → Appareils et services*. Le boîtier est découvert automatiquement (mDNS `_tcci._tcp`). Sinon : *Ajouter une intégration → TCCI*.

| Champ | Valeur |
|---|---|
| URL | `http://tcci.local` (ou l'IP du boîtier), ou `https://ton-serveur-tcci` |
| Jeton | boîtier : son code d'accès, s'il en a un · cloud : jeton d'accès créé sur la page TCCI (*Réglages → Jetons d'accès*) |

## Entités

| Entité | Contenu |
|---|---|
| `sensor.tcci_etat` | levé / au lit / éveillé au lit |
| `binary_sensor.tcci_au_lit` | au lit ou non |
| `sensor.tcci_dernier_appui` | horodatage du dernier appui |
| temps de sommeil, temps au lit, efficacité, latence, éveils, éveil nocturne, sieste, coucher, lever | nuit en cours ou dernière nuit |
| `button.tcci_bouton_1/2`, `button.tcci_annuler` | les boutons du boîtier |

Mise à jour toutes les 20 s. Les `entity_id` exacts sont visibles sur la page de l'appareil.

## Événement `tcci_event`

Il est déclenché à chaque nouvel appui. `kind` vaut `bed` (coucher), `up` (lever), `wake` (réveil), `sleep` (rendormi) ou `s` (somnolence). L'événement porte aussi `time`, `in_bed` et `awake`.

```yaml
triggers:
  - trigger: event
    event_type: tcci_event
    event_data: { kind: bed }
actions:
  - action: light.turn_off
    target: { area_id: chambre }
```

Note : chaque appui est une donnée de la thérapie. N'automatise pas les boutons `button.tcci_*` sans en avoir l'intention.
