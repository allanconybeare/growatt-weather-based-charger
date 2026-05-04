# Documentation Index

**Welcome!** This is the comprehensive documentation for the Growatt weather-based overnight charger. Choose your path below:

---

## 🚀 Getting Started

### New to the project?
- **[Quick Start](../README.md)** – Get the system running in 5 minutes
- **[Setup Guide](guides/DEPLOYMENT_READY.md)** – Initial installation & configuration
- **[Configuration Options](reference/)** – All settings explained

### Already running it?
- **[Troubleshooting](guides/)** – Common issues & fixes
- **[Configuration Reference](reference/)** – Deep dive into settings

---

## 📚 Documentation Structure

### 📖 [Guides](guides/)
**Step-by-step how-to documentation**

- **INVERTER_STATUS_CHECK.md** – Monitor inverter health, detect offline events, configure email/desktop alerts
- **PEAK_WINDOW_CONFIG_GUIDE.md** – Configure afternoon peak window checking
- **multi_provider_setup_guide.md** – Add and manage forecast providers
- **DEPLOYMENT_READY.md** – Deployment checklist and production setup

### 📋 [Reference](reference/)
**Technical deep-dives and architecture**

- **ARCHITECTURE_DIAGRAMS.md** – System design and component interactions
- **CHARGE_RATE_FIX.md** – How the charge rate calculation works
- **BATTERY_HEALTH_AND_CHARGE_RATE_ANALYSIS.md** – Battery charging logic explained
- **OLD_VS_NEW_THRESHOLDS.md** – Changes to SOC thresholds

### 👨‍💻 [Development](development/)
**For developers contributing to the project**

- *(Coming soon: Contributing guide, code style, testing)*

### 📦 [Archive](archive/)
**Historical documentation, session notes, and analysis**

- Older summaries and session logs
- Previous implementation details
- Historical analysis and planning docs

---

## 🎯 Common Tasks

### I want to...

#### ...configure the peak window (afternoon charging)
→ Read **[PEAK_WINDOW_CONFIG_GUIDE.md](guides/PEAK_WINDOW_CONFIG_GUIDE.md)**

#### ...monitor the inverter for offline/fault events
→ Read **[INVERTER_STATUS_CHECK.md](guides/INVERTER_STATUS_CHECK.md)**

#### ...add a new forecast provider
→ Read **[multi_provider_setup_guide.md](guides/multi_provider_setup_guide.md)**

#### ...understand how battery charging works
→ Read **[BATTERY_HEALTH_AND_CHARGE_RATE_ANALYSIS.md](reference/BATTERY_HEALTH_AND_CHARGE_RATE_ANALYSIS.md)**

#### ...set up for production
→ Read **[DEPLOYMENT_READY.md](guides/DEPLOYMENT_READY.md)**

#### ...understand the system architecture
→ Read **[ARCHITECTURE_DIAGRAMS.md](reference/ARCHITECTURE_DIAGRAMS.md)**

#### ...see what changed in charge rate calculations
→ Read **[CHARGE_RATE_FIX.md](reference/CHARGE_RATE_FIX.md)**

---

## 📁 File Organization

```
docs/
├── README.md              ← You are here
│
├── guides/               # How-to guides and tutorials
│   ├── INVERTER_STATUS_CHECK.md
│   ├── PEAK_WINDOW_CONFIG_GUIDE.md
│   ├── multi_provider_setup_guide.md
│   └── DEPLOYMENT_READY.md
│
├── reference/            # Technical references
│   ├── ARCHITECTURE_DIAGRAMS.md
│   ├── CHARGE_RATE_FIX.md
│   ├── BATTERY_HEALTH_AND_CHARGE_RATE_ANALYSIS.md
│   └── OLD_VS_NEW_THRESHOLDS.md
│
├── development/          # Developer docs (coming soon)
│
└── archive/              # Old/historical docs
    ├── SESSION_SUMMARY_NOV14.md
    ├── IMPLEMENTATION_CHANGES.md
    └── ... (other dated docs)
```

---

## 🔍 Quick Navigation

| Need | File | Purpose |
|------|------|------------------------------------------------------|
| Inverter monitoring | `INVERTER_STATUS_CHECK.md` | Set up offline detection & alerts |
| Configuration example | `PEAK_WINDOW_CONFIG_GUIDE.md` | Learn peak window settings |
| System design | `ARCHITECTURE_DIAGRAMS.md` | Understand components |
| Charging logic | `BATTERY_HEALTH_AND_CHARGE_RATE_ANALYSIS.md` | How rate is calculated |
| Production setup | `DEPLOYMENT_READY.md` | Get ready to deploy |
| New forecast source | `multi_provider_setup_guide.md` | Add provider |
| What changed | `CHARGE_RATE_FIX.md` | See improvements |
| History | `archive/` | Session notes & analysis |

---

## 📞 Still Can't Find It?

- Check the **main [README.md](../README.md)** in root (high-level overview)
- Look in **[archive/](archive/)** for historical context
- Review **[guides/](guides/)** for step-by-step help

---

**Last Updated**: May 4, 2026
**Status**: ✅ Active & Current
