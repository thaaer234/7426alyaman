# -*- coding: utf-8 -*-
"""
Usage (PowerShell from project root):
  python tools_inject_models_fix.py
It will:
  - Open accounts/models.py
  - Replace the stray line "(self, user):" with "def withdraw(self, user):"
  - Try to inject the 'clean' method into the first class that looks like a receipt model.
    (class name contains 'Receipt' or 'Payment')
  - Create a backup at accounts/models.py.bak
"""
import io, re, os, sys

ROOT = os.getcwd()
PATH = os.path.join(ROOT, "accounts", "models.py")
BACKUP = PATH + ".bak"

if not os.path.exists(PATH):
    print("ERROR: accounts/models.py not found at", PATH)
    sys.exit(1)

with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

# Backup
with io.open(BACKUP, "w", encoding="utf-8") as f:
    f.write(src)

# 1) Fix the bad function header
src_fixed = src.replace("(self, user):", "def withdraw(self, user):")

# 2) Ensure helper imports exist
need_helpers = ("from decimal import Decimal", "from django.core.exceptions import ValidationError", "from django.db.models import Sum")
for h in need_helpers:
    if h not in src_fixed:
        src_fixed = src_fixed.replace("from django.db import models", "from django.db import models\n"+h)

# 3) Inject clean() into a likely receipt class
snippet = """

    # --- Injected by tools_inject_models_fix.py ---
    def clean(self):
        from decimal import Decimal, InvalidOperation
        from django.core.exceptions import ValidationError
        from django.db.models import Sum

        def _dec(x, default="0"):
            if x is None:
                return Decimal(default)
            try:
                return Decimal(x)
            except (InvalidOperation, TypeError):
                return Decimal(default)

        def _get_enrollment_net(enrollment):
            for attr in ["net_amount", "total_after_discount", "net_total", "final_amount"]:
                val = getattr(enrollment, attr, None)
                if val is not None:
                    return _dec(val)
            price = getattr(enrollment, "price", None)
            amount = getattr(enrollment, "amount", None)
            gross = _dec(price) if price is not None else _dec(amount)
            disc_amt = _dec(getattr(enrollment, "discount_amount", None))
            disc_pct = _dec(getattr(enrollment, "discount_percent", None))
            net_by_pct = gross * (Decimal("1") - (disc_pct / Decimal("100"))) if disc_pct else gross
            net = net_by_pct - disc_amt
            if net < 0:
                net = Decimal("0")
            return net

        if getattr(self, "enrollment_id", None):
            net = _get_enrollment_net(self.enrollment)
            paid_before = (
                type(self).objects.filter(enrollment=self.enrollment)
                .exclude(pk=self.pk)
                .aggregate(s=Sum("paid_amount"))
                .get("s") or Decimal("0")
            )
            paid_before = _dec(paid_before)
            this_paid = _dec(getattr(self, "paid_amount", None))
            remaining_before = net - paid_before
            if remaining_before < 0:
                remaining_before = Decimal("0")
            if this_paid > remaining_before:
                raise ValidationError({
                    "paid_amount": f"المبلغ المدفوع ({this_paid}) يتجاوز المتبقّي على التسجيل ({remaining_before})."
                })
            if hasattr(self, "remaining"):
                self.remaining = net - (paid_before + this_paid)
                if self.remaining < 0:
                    self.remaining = Decimal("0")
        else:
            pass
"""

# Find a class likely to be a receipt model
m = re.search(r"class\s+([A-Za-z_]*(Receipt|Payment)[A-Za-z_]*)\s*\(.*?\):", src_fixed)
if m:
    cls_start = m.end()
    # Insert snippet after class header
    src_fixed = src_fixed[:cls_start] + snippet + src_fixed[cls_start:]
else:
    print("WARNING: No class containing 'Receipt' or 'Payment' found. Only fixed the syntax error.")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src_fixed)

print("OK: Patched accounts/models.py. Backup at", BACKUP)
