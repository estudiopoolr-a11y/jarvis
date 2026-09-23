---
name: split-kebo-presupuestos
description: Split kebo.py and presupuestos.py into domain modules
metadata:
  type: project
---

Split app/routes/kebo.py into app/routes/kebo/{accounts,transactions,budgets,reports,export,seed}.py and modules/nlp/parsers/presupuestos.py into modules/nlp/parsers/budgets/{create,update,delete,query,bulk}.py while keeping compatibility facades.

**Why:** To reduce file sizes and improve separation of concerns, following the pattern established in the previous reorganization (modules/finance/reports.py and modules/nlp/actions/*).

**How to apply:** The split was performed via a one-shot script that preserved imports and behavior. All tests pass (20/20). The API endpoints remain unchanged; internal imports were updated to use the new modules.

Related: [[agents-reorg-phase-1]] (previous centralization of reports and actions).