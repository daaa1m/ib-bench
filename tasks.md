# IB-Bench Task List

## Status Legend

| Status | Meaning |
|--------|---------|
| **Ready** | Complete with prompt.md, rubric.json, and input files |
| **Needs Input** | Has meta.yaml but missing input files |
| **Idea** | Just a blurb/concept, needs full development |
| **Empty** | Folder exists but no content |

---

## Easy Tasks

| ID | Status | Type | Category | Description |
|----|--------|------|----------|-------------|
| e-001 | Ready | fix-error | excel | Find error in LBO model causing unbalanced balance sheet (row 140 missing row 138 in formula) |
| e-002 | Ready | summarise | pdf | Summarize Grant's Interest Rate Observer article |
| e-003 | Ready | extraction | web | Extract AMZN's next 24-month unconditional purchase obligations from 10-K (USD 16,477m) |
| e-004 | Ready | extraction | web | Reconcile AMD Q3 2025 GAAP to non-GAAP operating income with all line items |
| e-005 | Ready | extraction | pdf | Extract AMZN Q3 2025 key metrics + write one-page earnings summary |
| e-006 | Ready | fix-error | excel | Add circularity to LBO model interest calculation (verify row 164 values) |
| e-007 | Ready | summarise | pdf | Synthesize GS/JPM Alphabet Q3'25 research reports + extract metrics from models |
| e-008 | Needs Input | summarise | pdf | Summarize MD&A section from 10-K focusing on business drivers and risks |
| e-009 | Needs Input | extraction | excel | Extract and list all key assumptions from existing LBO model |
| e-010 | Idea | fix-error | excel | Fix multiple errors in Excel model |
| e-011 | Needs Input | extraction | pdf | Extract debt maturity schedule from credit agreement or 10-K footnotes |
| e-012 | Needs Input | summarise | pdf | Summarize top 5 risk factors from S-1 filing with analyst implications |
| e-013 | Idea | creating | pdf | Generate DD questions for management meeting after reviewing materials |
| e-014 | Needs Input | fix-error | excel | Fix date/period alignment errors in quarterly projection model |
| e-015 | Idea | summarise | web | Create summary of all acquisitions done by roll-ups |
| e-016 | Needs Input | summarise | pdf | Summarize key economic terms from merger agreement |
| e-017 | Needs Input | extraction | web | Find 5 comparable M&A transactions with EV/EBITDA multiples for given sector |
| e-018 | Needs Input | fix-error | excel | Fix incorrect NWC formula (wrong sign or missing component) in cash flow |
| e-019 | Needs Input | extraction | pdf | Extract financial covenants from credit agreement |
| e-020 | Idea | fix-error | excel | Check LBO model - answer is nothing is wrong (tests false positive resistance) |

---

## Medium Tasks

| ID | Status | Type | Category | Description |
|----|--------|------|----------|-------------|
| m-001 | Idea | creating | web | Generate PIB from publicly available materials (use Moody's Corp) |
| m-002 | Idea | fix-error | excel | Update model with latest quarterly/annual numbers (use KEX-model.xlsx) |
| m-003 | Idea | fix-error | excel | Check error in copying model historical financials (use GOOG model) |
| m-004 | Idea | creating | web | Generate target list of private companies with contact details (sourcing work) |
| m-005 | Idea | creating | excel | COGS build - model how much to reduce COGS and SG&A with justification |
| m-006 | Idea | creating | excel | Build model drivers with assumptions and business assessment (use WMT/Albertsons) |
| m-007 | Idea | creating | excel | Build detailed depreciation schedule for asset-heavy company using footnotes |
| m-008 | Idea | extraction | pdf+excel | Populate 3-statement model template with 3 years historicals from 10-K |
| m-009 | Idea | summarise | pdf | Compare two CIMs from same sector - identify key differences and implications |
| m-010 | Idea | creating | excel+pdf | Build operating model from skeleton template + investment memo with assumptions |

---

## Hard Tasks

| ID | Status | Type | Category | Description |
|----|--------|------|----------|-------------|
| h-001 | Idea | creating | excel | Given sample LBO model and memo, generate another one on a public company |
| h-002 | Idea | creating | excel | Generate debt schedule for TWTR LBO and extract key terms |
| h-003 | Idea | creating | excel | Given 3-statement model and memo, generate another on a public company |
| h-004 | Idea | fix-error | excel | Update model with restated financials (use WILD model) - human expert judge |
| h-005 | Idea | analysis | pdf | Bankruptcy viability analysis of Rite Aid - human expert scoring |
| h-007 | Idea | creating | excel | VC fundraising model - dilution, post-money, pre-money calculations |

---

## Private Test Set (eval/tasks/_private/)

### Easy (Private)

| ID | Status | Type | Category | Description |
|----|--------|------|----------|-------------|
| e-021 | Idea | fix-error | pdf | Spot errors in PDF where numbers don't tie (EBITDA calc, segment sums) |
| e-022 | Idea | creating | excel | Build pro forma balance sheet from transaction assumptions |
| e-023 | Idea | creating | excel | Build sources and uses table for an acquisition |
| e-024 | Idea | extraction | pdf | Extract capitalization table from CIM/10-K, calculate fully diluted shares |
| e-025 | Idea | extraction | pdf | Pull management projections from CIM into clean table with growth rates |
| e-026 | Idea | creating | excel | Build simple 2-way sensitivity table (IRR vs entry/exit multiples) |

### Hard (Private)

| ID | Status | Type | Category | Description |
|----|--------|------|----------|-------------|
| h-006 | Idea | creating | excel | Given very messy data, generate a 3-statement model |
| h-007 | Idea | creating | excel | Merger model on 2 public companies |

---

## Summary

| Difficulty | Ready | Needs Input | Idea | Empty | Total |
|------------|-------|-------------|------|-------|-------|
| Easy (e-) | 7 | 9 | 4 | 0 | 20 |
| Medium (m-) | 0 | 0 | 10 | 0 | 10 |
| Hard (h-) | 0 | 0 | 6 | 0 | 6 |
| Private Easy | 0 | 0 | 6 | 0 | 6 |
| Private Hard | 0 | 0 | 2 | 0 | 2 |
| **Total** | **7** | **9** | **28** | **0** | **44** |

---

## Notes

### Task Types
- **fix-error**: Find and correct errors in existing models/documents
- **summarise**: Create concise summaries of financial documents
- **extraction**: Pull specific data points from sources
- **creating**: Build models, schedules, or analysis from scratch
- **analysis**: Interpret data and provide structured insights

### Difficulty Calibration
- **Easy (<1 hour)**: Single-step tasks, finding specific data, simple fixes, short summaries
- **Medium (few hours)**: Multi-step analysis, building simple models, cross-referencing sources
- **Hard (days)**: Full model builds, complex multi-document analysis, complete deliverables

### Priority
1. Complete "Needs Input" easy tasks (have meta.yaml, just need files)
2. Develop "Idea" easy tasks into full specs
3. Move to medium/hard tasks once easy set is solid
