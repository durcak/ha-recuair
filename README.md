# Recuair pre Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![GitHub release](https://img.shields.io/github/v/release/durcak/ha-recuair?include_prereleases&sort=semver)](https://github.com/durcak/ha-recuair/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.4%2B-03A9F4.svg)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Neoficiálna integrácia pre lokálne rekuperačné jednotky **[Recuair](https://www.recuair.com)** (testované na **DC40**).
Číta hodnoty a **ovláda jednotku priamo v lokálnej sieti** – bez cloudu. Voliteľne sa dá pripojiť aj účet
[recuair.enobis.eu](https://recuair.enobis.eu) pre údaje, ktoré lokálne rozhranie neposkytuje.

*English summary [below](#english).*

> [!NOTE]
> **Beta** – ak niečo nefunguje, založte prosím [issue](https://github.com/durcak/ha-recuair/issues) aj s modelom
> jednotky, verziou firmvéru a logom.

## Funkcie

**Lokálne (bez cloudu)**
- 🌬️ **Ventilátor** – Auto, stupne 1–4, Holiday, Bypass, vypnutie (entita `fan` aj výber režimu)
- 💡 **Náladové osvetlenie** – farba RGB a jas (5 stupňov)
- 📈 Senzory: CO₂, teplota dnu a vonku, vlhkosť, **intenzita vetrania**, opotrebenie filtra, režim, firmvér
- 📊 Všetky merané hodnoty majú **dlhodobé štatistiky** (grafy na týždne a mesiace)

**Voliteľne z cloudu Recuair**
- ⚙️ Otáčky oboch ventilátorov (ot/min)
- ♻️ **Zrekuperovaná energia** (kWh)
- 💧 Vlhkosť vonku, stav filtra, chybové hlásenia

## Inštalácia

### HACS (odporúčané)

[![Otvoriť repozitár v HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=durcak&repository=ha-recuair&category=integration)

1. Kliknite na tlačidlo vyššie, alebo v HACS **⋮ → Vlastné repozitáre** pridajte `https://github.com/durcak/ha-recuair`
   s kategóriou **Integrácia**.
2. Nainštalujte **Recuair** a reštartujte Home Assistant.

### Ručne

Skopírujte `custom_components/recuair` do `config/custom_components/` a reštartujte Home Assistant.

### Prechod z pôvodnej integrácie Recuair

Ak ste používali staršiu integráciu s doménou `recuair` (repozitár `pavelkrejsa/recuair-ha` už neexistuje), stačí
ju prepísať touto verziou. Nastavenia aj entity sa **prevedú automaticky** a história zostane zachovaná.

## Nastavenie

[![Pridať integráciu](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=recuair)

1. **Adresa jednotky** – IP adresa jednotky (odporúčané, napr. `192.168.1.57`) alebo `recuair.local`.
   Nájdete ju v routeri; webové rozhranie jednotky sa otvára na `http://<adresa>/`.
2. **Účet Recuair (voliteľné)** – e-mail a heslo do [recuair.enobis.eu](https://recuair.enobis.eu). Ak cloud
   nepotrebujete, nechajte prázdne. Dá sa doplniť aj neskôr cez **Konfigurovať**.

Odporúčame jednotke v routeri nastaviť **pevnú IP adresu (DHCP rezerváciu)** – inak sa po reštarte môže zmeniť.

## Entity

| Entita | Popis |
|---|---|
| Ventilátor (`fan`) | zapnutie/vypnutie, rýchlosť 25/50/75/100 % = stupne 1–4, predvoľby Auto/Holiday/Bypass; v režime Auto ukazuje skutočnú intenzitu |
| Režim vetrania (`select`) | Auto, 1–4, Holiday, Bypass, Vypnuté |
| Náladové osvetlenie (`light`) | farba a jas |
| CO₂, Teplota dnu/vonku, Vlhkosť | merané hodnoty jednotky |
| Intenzita vetrania | aktuálny výkon vetrania v % |
| Opotrebenie filtra | koľko percent životnosti filtra je spotrebovaných |
| Otáčky ventilátora 1/2, Zrekuperovaná energia, Vlhkosť vonku, Stav filtra, Chyby | len s cloudom |

## Bezpečnostné upozornenie

Webové rozhranie jednotky nie je chránené heslom a v nastaveniach zobrazuje **heslo vašej Wi-Fi v čitateľnej
podobe**. Ktokoľvek vo vašej sieti ho môže prečítať. Integrácia toto pole nikdy nečíta ani neukladá. Zvážte
umiestnenie jednotky do oddelenej siete pre IoT zariadenia (VLAN / sieť pre hostí).

## Riešenie problémov

```yaml
logger:
  logs:
    custom_components.recuair: debug
```

- **Jednotka nie je dostupná** – skúste IP adresu namiesto `recuair.local` a overte, že sa
  `http://<adresa>/` otvorí v prehliadači.
- **Cloud: nesprávne údaje** – overte prihlásenie na [recuair.enobis.eu](https://recuair.enobis.eu).

## Licencia

[MIT](LICENSE). Nejde o oficiálny produkt spoločnosti Recuair.

---

## English

Unofficial Home Assistant integration for **Recuair** decentralised heat-recovery ventilation units (tested with
**DC40**). It reads the unit's local web interface and **controls it locally** – fan (Auto, speeds 1–4, Holiday,
Bypass, off), RGB mood light, and sensors for CO₂, temperatures, humidity, ventilation intensity and filter wear,
all with long-term statistics. Optionally, signing in to the Recuair cloud (recuair.enobis.eu) adds fan RPMs,
recovered energy, outside humidity and filter/error state. Install via HACS as a custom repository. Existing
configurations of the older `recuair` integration are migrated automatically.
