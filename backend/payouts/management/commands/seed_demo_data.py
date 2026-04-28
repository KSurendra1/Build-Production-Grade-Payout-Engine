from django.core.management.base import BaseCommand
from django.db import transaction

from payouts.models import LedgerEntry, Merchant


class Command(BaseCommand):
    help = "Seed 3 demo merchants and credit-ledger history."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing merchants and ledger entries before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            LedgerEntry.objects.all().delete()
            Merchant.objects.all().delete()
            self.stdout.write(self.style.WARNING("Existing merchant and ledger data cleared."))

        m1 = Merchant.objects.create(name="Acme Foods")
        m2 = Merchant.objects.create(name="Delta Retail")
        m3 = Merchant.objects.create(name="Nimbus Labs")

        LedgerEntry.objects.bulk_create(
            [
                LedgerEntry(merchant=m1, amount_paise=250000, entry_type=LedgerEntry.CREDIT),
                LedgerEntry(merchant=m1, amount_paise=80000, entry_type=LedgerEntry.CREDIT),
                LedgerEntry(merchant=m2, amount_paise=120000, entry_type=LedgerEntry.CREDIT),
                LedgerEntry(merchant=m2, amount_paise=95000, entry_type=LedgerEntry.CREDIT),
                LedgerEntry(merchant=m3, amount_paise=500000, entry_type=LedgerEntry.CREDIT),
            ]
        )

        self.stdout.write(self.style.SUCCESS("Demo merchants and credit history seeded."))
        self.stdout.write(f"- {m1.name}: {m1.id}")
        self.stdout.write(f"- {m2.name}: {m2.id}")
        self.stdout.write(f"- {m3.name}: {m3.id}")

