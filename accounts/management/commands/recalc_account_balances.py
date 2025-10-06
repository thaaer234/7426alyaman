from django.core.management.base import BaseCommand
from accounts.models import Account


class Command(BaseCommand):
    help = "Recalculate all account balances as own net + sum of children (bottom-up)."

    def handle(self, *args, **kwargs):
        def depth(a):
            d, p = 0, a.parent
            while p:
                d += 1
                p = p.parent
            return d
        accs = list(Account.objects.all())
        for a in sorted(accs, key=depth, reverse=True):
            a.recalc_with_children()
        self.stdout.write(self.style.SUCCESS("Balances fully recalculated."))
