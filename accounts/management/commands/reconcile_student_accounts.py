from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import (
    Account,
    StudentReceipt,
    Studentenrollment,
)
from students.models import Student as StudentProfile


class Command(BaseCommand):
    help = (
        "Reconcile student AR accounts, enrollments and receipts: "
        "- ensure each student has an AR account and is linked to it\n"
        "- ensure enrollment accounts and opening entries exist\n"
        "- create missing journal entries for receipts\n"
        "- rebuild account balances"
    )

    def handle(self, *args, **options):
        created_ar = 0
        fixed_flags = 0
        linked_students = 0
        receipts_posted = 0
        receipts_failed = 0
        enrollments_fixed = 0

        # Ensure AR parent exists
        ar_parent, _ = Account.objects.get_or_create(
            code='1120',
            defaults={
                'name': 'Accounts Receivable',
                'name_ar': 'الذمم المدينة',
                'account_type': 'ASSET',
                'is_active': True,
            },
        )

        # 1) Ensure each student has AR account and link it
        for student in StudentProfile.objects.all():
            try:
                acc = Account.get_or_create_student_ar_account(student)
                if not student.account_id:
                    student.account_id = acc.id
                    student.save(update_fields=['account'])
                    linked_students += 1
                # Ensure parent and flags
                need_save = False
                if acc.parent_id != ar_parent.id:
                    acc.parent = ar_parent
                    need_save = True
                if not acc.is_student_account:
                    acc.is_student_account = True
                    need_save = True
                if not acc.student_name:
                    acc.student_name = student.full_name
                    need_save = True
                if need_save:
                    acc.save(update_fields=['parent', 'is_student_account', 'student_name'])
                    fixed_flags += 1
            except Exception as e:
                self.stderr.write(f"Student {student.id} '{student.full_name}': {e}")

        # 2) Ensure enrollment accounts and opening entries
        for enr in Studentenrollment.objects.all():
            try:
                enr.ensure_enrollment_accounts()
                # Create opening accrual if missing and amount > 0
                try:
                    if not getattr(enr, 'opened_journal_entry_id', None) and enr.net_tuition > 0:
                        # Use creator if known, else any superuser later (skipped here)
                        user = getattr(enr, '_created_by', None)
                        enr.post_opening_entry(user)
                        enrollments_fixed += 1
                except Exception:
                    # Best-effort only; continue
                    pass
            except Exception as e:
                self.stderr.write(f"enrollment {enr.id}: {e}")

        # 3) Create missing journal entries for receipts
        for r in StudentReceipt.objects.all().select_related('created_by', 'journal_entry'):
            try:
                if r.journal_entry_id is None:
                    r.create_accrual_journal_entry(r.created_by)
                    receipts_posted += 1
                else:
                    # If entry exists but not posted, post it
                    if not r.journal_entry.is_posted:
                        r.journal_entry.post_entry(r.created_by)
                        receipts_posted += 1
            except Exception as e:
                receipts_failed += 1
                self.stderr.write(
                    f"Receipt {r.id} ({r.receipt_number or 'NO#'}): failed to create/post journal entry: {e}"
                )

        # 4) Rebuild balances bottom-up for safety
        Account.rebuild_all_balances()

        # Summary
        self.stdout.write(self.style.SUCCESS(
            "Reconciliation complete:\n"
            f"  Students linked to AR: {linked_students}\n"
            f"  Student AR flags fixed: {fixed_flags}\n"
            f"  enrollments fixed: {enrollments_fixed}\n"
            f"  Receipts posted/updated: {receipts_posted}\n"
            f"  Receipts failed: {receipts_failed}"
        ))

