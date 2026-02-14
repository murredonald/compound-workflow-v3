# LinkedIn post — TR04: temporal versioning

The Belgian corporate tax rate is 25%.

It's also 29.58%. And 33.99%.

All three are correct — depending on which year you're asking about.

Before 2018: 33.99%
2018-2019: 29.58%
2020+: 25%

Ask a generic AI tool "what is the Belgian corporate tax rate?" and you get one number. No indication of which period. No warning that it was different three years ago. No context that a 2019 filing uses a completely different rate than 2024.

This is the temporal versioning problem.

Belgian tax law changes at least twice per year through program laws. In 2023-2024 alone:
- Notional interest deduction: abolished
- Pillar Two minimum tax: introduced
- Capital gains tax: 10% from January 1, 2026
- Inheritance tax: reformed in Flanders (2026), Wallonia (2028)

Each change creates a new version of existing provisions. Each version is the correct answer — for its period.

A system without temporal versioning cannot distinguish between law-as-it-was and law-as-it-is. And for Belgian tax, that's the difference between the right answer and the right answer for the wrong year.

We wrote up the full architecture: [link]

#BelgianTax #LegalAI #TemporalVersioning #DataFreshness #AurythTX
