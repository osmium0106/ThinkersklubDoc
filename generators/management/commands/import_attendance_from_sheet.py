from django.core.management.base import BaseCommand
from generators.models import Employee, EmployeeAttendance
from generators.google_sheet_utils import fetch_google_sheet_csv

# Map sheet names to employee names in your DB
SHEET_EMPLOYEE_MAP = {
    'Aman': 'Aman Singh',
    'Abhay': 'Abhay Singh',
    'Mayank': 'Mayank Singh',
}

# Google Sheet CSV URLs for each sheet (gid param for each tab)
SHEET_URLS = {
    'Aman': 'https://docs.google.com/spreadsheets/d/1vZx7K37vLLbVqshb3KHMui35GNb9Se286mMu2RM8uIg/export?format=csv&gid=0',
    'Abhay': 'https://docs.google.com/spreadsheets/d/e/2PACX-1vQh3Faxce0kIaz7qK1K6ip5thHakRsK8JGJguGKxeEvJFfvzwpqKjVuSgQ0SxSU5JP6DaYUT8jfirIQ/pub?gid=0&single=true&output=csv',
    'Mayank': 'https://docs.google.com/spreadsheets/d/e/2PACX-1vQh3Faxce0kIaz7qK1K6ip5thHakRsK8JGJguGKxeEvJFfvzwpqKjVuSgQ0SxSU5JP6DaYUT8jfirIQ/pub?gid=515633561&single=true&output=csv',
}

class Command(BaseCommand):
    help = 'Import employee attendance from Google Sheets (one sheet per employee, Month in col A, Total Present in col AG)'

    def handle(self, *args, **options):
        for sheet, emp_name in SHEET_EMPLOYEE_MAP.items():
            url = SHEET_URLS[sheet]
            rows = fetch_google_sheet_csv(url)
            try:
                employee = Employee.objects.get(name=emp_name)
            except Employee.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Employee not found: {emp_name}'))
                continue
            for row in rows:
                month = row.get('Month')
                year = row.get('Year') or row.get('year') or ''
                total_present = row.get('AG') or row.get('Total Present')
                if not (month and year and total_present):
                    continue
                try:
                    total_present = int(float(total_present))
                except Exception:
                    continue
                obj, created = EmployeeAttendance.objects.update_or_create(
                    employee=employee, month=month, year=year,
                    defaults={'total_present': total_present}
                )
            self.stdout.write(self.style.SUCCESS(f'Imported attendance for {emp_name}'))
        self.stdout.write(self.style.SUCCESS('Attendance import complete.'))
