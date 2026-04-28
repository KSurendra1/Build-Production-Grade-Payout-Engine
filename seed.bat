@echo off
echo Running migrations...
docker-compose exec backend python manage.py migrate

echo Seeding database...
docker-compose exec backend python manage.py shell -c "from payouts.models import Merchant, LedgerEntry; m = Merchant.objects.create(id='00000000-0000-0000-0000-000000000000', name='Demo Merchant'); LedgerEntry.objects.create(merchant=m, amount_paise=10000000, entry_type='CREDIT')"

echo Done! The project is ready.
