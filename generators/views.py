from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
import os
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from io import BytesIO
from django.views.decorators.csrf import csrf_exempt
from .models import School, Employee, EmployeeAttendance
from .google_sheet_utils import fetch_google_sheet_csv

def home(request):
    employees = Employee.objects.all()
    schools = School.objects.all()
    attendances = EmployeeAttendance.objects.select_related('employee').all().order_by('-year', '-month')
    return render(request, 'generators/home.html', {
        'employees': employees,
        'schools': schools,
        'attendances': attendances,
    })

def get_next_invoice_number():
    # Simple file-based counter for demo; in production use a DB model
    counter_file = 'invoice_counter.txt'
    prefix = 'TK25'
    if not os.path.exists(counter_file):
        with open(counter_file, 'w') as f:
            f.write('1')
        return f'{prefix}001'
    with open(counter_file, 'r+') as f:
        num = int(f.read().strip())
        next_num = num + 1
        f.seek(0)
        f.write(str(next_num))
        f.truncate()
    return f'{prefix}{str(num).zfill(3)}'

def invoice(request):
    if request.method == 'GET':
        invoice_number = get_next_invoice_number()
        today = timezone.now().date()
        due_date = today + timedelta(days=15)
        schools = School.objects.all()
        employees = Employee.objects.all()
        # Get current month and year for attendance lookup
        invoice_month = today.strftime('%B')
        invoice_year = today.year
        # Build a dict: {employee_name: total_present}
        attendance_map = {}
        for emp in employees:
            att = EmployeeAttendance.objects.filter(employee=emp, month=invoice_month, year=invoice_year).first()
            attendance_map[emp.name] = att.total_present if att else ''
        context = {
            'invoice_number': invoice_number[4:],
            'invoice_date': today.strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
            'schools': schools,
            'employees': employees,
            'attendance_map': attendance_map,
            'invoice_month': invoice_month,
            'invoice_year': invoice_year,
        }
        return render(request, 'generators/invoice.html', context)
    elif request.method == 'POST':
        # Calculate subtotal as sum of all total_salary values
        total_salaries = [float(x or 0) for x in request.POST.getlist('total_salary[]')]
        subtotal = sum(total_salaries)
        taxes = float(request.POST.get('taxes') or 0)
        gst_percent = float(request.POST.get('gst_percent') or 0)
        gst_amount = float(request.POST.get('gst_amount') or 0)
        other_charges = float(request.POST.get('other_charges') or 0)
        discount = float(request.POST.get('discount') or 0)
        paid_amount = float(request.POST.get('paid_amount') or 0)
        pay_date = request.POST.get('pay_date') or ''
        pay_mode = request.POST.get('pay_mode') or ''
        pay_ref = request.POST.get('pay_ref') or ''
        # Calculate GST amount if not provided
        if not gst_amount:
            gst_amount = subtotal * gst_percent / 100
        total = subtotal + taxes + gst_amount + other_charges - discount - paid_amount
        # Amount in words (simple, Indian style)
        def number_to_words(num):
            a = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
            b = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
            def in_words(n):
                if n < 20: return a[int(n)]
                if n < 100: return b[int(n//10)] + ('' if n%10==0 else ' ' + a[int(n%10)])
                if n < 1000: return a[int(n//100)] + ' Hundred' + ('' if n%100==0 else ' and ' + in_words(n%100))
                if n < 100000: return in_words(n//1000) + ' Thousand' + ('' if n%1000==0 else ' ' + in_words(n%1000))
                if n < 10000000: return in_words(n//100000) + ' Lakh' + ('' if n%100000==0 else ' ' + in_words(n%100000))
                return ''
            return in_words(int(num)) + ' Rupees Only' if num else 'Zero'
        amount_words = number_to_words(total)
        context = {
            'invoice_number': request.POST.get('invoice_number'),
            'invoice_date': request.POST.get('invoice_date'),
            'due_date': request.POST.get('due_date'),
            'school_name': request.POST.get('school_name'),
            'school_address': 'Gorabarik, Sultanpur, Uttar Pradesh 228001',
            'contact_person': 'Mr. Ranjeet Singh',
            'school_contact': '+91 9818812007',
            'trainers': zip(
                request.POST.getlist('trainer_name[]'),
                request.POST.getlist('days[]'),
                request.POST.getlist('total_salary[]')
            ),
            'subtotal': f'{subtotal:.2f}',
            'taxes': f'{taxes:.2f}',
            'gst_percent': f'{gst_percent:.2f}',
            'gst_amount': f'{gst_amount:.2f}',
            'other_charges': f'{other_charges:.2f}',
            'discount': f'{discount:.2f}',
            'paid_amount': f'{paid_amount:.2f}',
            'total': f'{total:.2f}',
            'amount_words': amount_words,
            'pay_date': pay_date,
            'pay_mode': pay_mode,
            'pay_ref': pay_ref,
        }
        # Save Invoice to DB
        from .models import Invoice  # Only import Invoice here, not Employee
        school_name = request.POST.get('school_name')
        school = School.objects.filter(name=school_name).first()
        invoice_obj = Invoice.objects.create(
            invoice_number=request.POST.get('invoice_number'),
            school=school,
            invoice_date=request.POST.get('invoice_date'),
            due_date=request.POST.get('due_date'),
            subtotal=subtotal,
            taxes=taxes,
            gst_percent=gst_percent,
            gst_amount=gst_amount,
            other_charges=other_charges,
            discount=discount,
            paid_amount=paid_amount,
            month=request.POST.get('invoice_date').split('-')[1],
            year=request.POST.get('invoice_date').split('-')[0],
            total=total,
            pay_date=pay_date if pay_date else None,
            pay_mode=pay_mode,
            pay_ref=pay_ref,
        )
        # Optionally, save trainers as related data if your model supports it
        html = render_to_string('generators/invoice_pdf.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=Invoice_TK25{context["invoice_number"]}.pdf'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('Error generating PDF', status=500)
        return response

def salary_slip(request):
    from datetime import datetime
    current_year = datetime.now().year
    current_month = datetime.now().strftime('%B')
    if request.method == 'GET':
        employees = Employee.objects.all()
        # Build nested attendance map: {employee_name: {month: total_present}}
        attendance_map = {}
        for emp in employees:
            attendance_map[emp.name] = {}
            for att in emp.attendances.all():
                attendance_map[emp.name][att.month] = att.total_present
        return render(request, 'generators/salary_slip.html', {
            'year': current_year,
            'month': current_month,
            'current_year': current_year,
            'employees': employees,
            'attendance_map': attendance_map,
        })
    elif request.method == 'POST':
        employee_name = request.POST.get('employee_name')
        employee_id = request.POST.get('employee_id')
        designation = request.POST.get('designation')
        date_of_joining = request.POST.get('date_of_joining')
        pan_number = request.POST.get('pan_number')
        month = request.POST.get('month')
        year = request.POST.get('year')
        basic_salary = float(request.POST.get('basic_salary') or 0)
        allowances = float(request.POST.get('allowances') or 0)
        deductions = float(request.POST.get('deductions') or 0)
        net_salary = float(request.POST.get('net_salary') or 0)
        # Convert empty string to 0 for integer fields
        def parse_int(val):
            try:
                return int(val)
            except (TypeError, ValueError):
                return 0
        total_working_days = parse_int(request.POST.get('total_working_days'))
        days_present = parse_int(request.POST.get('days_present'))
        days_absent = parse_int(request.POST.get('days_absent'))
        overtime_hours = float(request.POST.get('overtime_hours') or 0)
        bank_account = request.POST.get('bank_account')
        payment_mode = request.POST.get('payment_mode')
        # Convert empty string to None for date fields
        payment_date = request.POST.get('payment_date') or None
        transaction_id = request.POST.get('transaction_id')
        authorized_signatory = request.POST.get('authorized_signatory') or 'Divyanshu Singh'
        context = {
            'employee_name': employee_name,
            'employee_id': employee_id,
            'designation': designation,
            'date_of_joining': date_of_joining,
            'pan_number': pan_number,
            'month': month,
            'year': year,
            'basic_salary': f'{basic_salary:.2f}',
            'allowances': f'{allowances:.2f}',
            'deductions': f'{deductions:.2f}',
            'net_salary': f'{net_salary:.2f}',
            'total_working_days': total_working_days,
            'days_present': days_present,
            'days_absent': days_absent,
            'overtime_hours': overtime_hours,
            'bank_account': bank_account,
            'payment_date': payment_date,
            'payment_mode': payment_mode,
            'transaction_id': transaction_id,
            'authorized_signatory': authorized_signatory,
        }
        # Save SalarySlip to DB
        from .models import SalarySlip  # Only import SalarySlip here, not Employee
        emp = Employee.objects.filter(name=employee_name).first()
        SalarySlip.objects.create(
            employee=emp,
            month=month,
            year=year,
            basic_salary=basic_salary,
            allowances=allowances,
            deductions=deductions,
            net_salary=net_salary,
            total_working_days=total_working_days,
            days_present=days_present,
            days_absent=days_absent,
            overtime_hours=overtime_hours,
            bank_account=bank_account,
            payment_date=payment_date,
            payment_mode=payment_mode,
            transaction_id=transaction_id,
            authorized_signatory=authorized_signatory,
        )
        html = render_to_string('generators/salary_slip_pdf.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=SalarySlip_{employee_id}_{month}_{year}.pdf'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('Error generating PDF', status=500)
        return response

def public_sheet_employees(request):
    # Replace with your actual public Google Sheet CSV export URL
    sheet_url = 'https://docs.google.com/spreadsheets/d/1vZx7K37vLLbVqshb3KHMui35GNb9Se286mMu2RM8uIg/export?format=csv'
    employees = fetch_google_sheet_csv(sheet_url)
    return render(request, 'generators/public_employees.html', {'employees': employees})
