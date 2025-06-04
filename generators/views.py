from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
import os
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from io import BytesIO

def home(request):
    return render(request, 'generators/home.html')

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
        context = {
            'invoice_number': invoice_number[4:],
            'invoice_date': today.strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
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
            html = render_to_string('generators/invoice_pdf.html', context)
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename=Invoice_TK25{context["invoice_number"]}.pdf'
            pisa_status = pisa.CreatePDF(html, dest=response)
            if pisa_status.err:
                return HttpResponse('Error generating PDF', status=500)
            return response
