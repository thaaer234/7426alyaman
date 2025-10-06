from django.core.management.base import BaseCommand
from accounts.models import Account
from django.db import transaction


class Command(BaseCommand):
    help = "Attach parent accounts based on code patterns (e.g., '1120-0003' -> parent '1120', and numeric roll-ups like 121 -> 111 -> 11 -> 1)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview changes without saving.')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        updated = 0

        # Build lookup by code for fast parent resolution
        codes = {a.code: a.id for a in Account.objects.all().only('id', 'code')}

        def resolve_parent_code(code: str):
            # hyphen child: take left side
            if '-' in code:
                return code.split('-', 1)[0]
            # numeric shrink: progressively trim from the right until a parent code exists
            s = code.rstrip()
            while len(s) > 1:
                s = s[:-1]
                if s in codes:
                    return s
            return None

        with transaction.atomic():
            for acc in Account.objects.select_for_update().all():
                if acc.parent_id:
                    continue
                pcode = resolve_parent_code(acc.code)
                if not pcode:
                    continue
                parent_id = codes.get(pcode)
                if not parent_id or parent_id == acc.id:
                    continue
                updated += 1
                self.stdout.write(f"{acc.code} -> parent {pcode}")
                if not dry:
                    acc.parent_id = parent_id
                    acc.save(update_fields=['parent_id'])
            if dry:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(f"Done. Linked: {updated}"))

