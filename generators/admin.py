from django.contrib import admin
from .models import School, Employee, Invoice, SalarySlip, EmployeeAttendance
from django.urls import path
from django.utils.html import format_html
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.http import HttpResponse
from xhtml2pdf import pisa

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "contact_person", "contact_number", "pan_number")
    search_fields = ("name", "address", "contact_person", "contact_number", "pan_number")

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("name", "employee_id", "designation", "date_of_joining", "pan_number", "bank_account", "basic_salary")
    search_fields = ("name", "employee_id", "designation", "pan_number", "bank_account")

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "school", "invoice_date", "month", "year", "total", "download_invoice")
    search_fields = ("invoice_number", "school__name", "month", "year")
    list_filter = ("school", "month", "year")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:invoice_id>/download/', self.admin_site.admin_view(self.download_invoice_view), name='generators_invoice_download'),
        ]
        return custom_urls + urls

    def download_invoice(self, obj):
        return format_html('<a class="button" href="{}">Download</a>', f'./{obj.id}/download/')
    download_invoice.short_description = 'Download PDF'
    download_invoice.allow_tags = True

    def download_invoice_view(self, request, invoice_id):
        invoice = get_object_or_404(Invoice, id=invoice_id)
        # Prepare context as in views.py
        context = {
            'invoice_number': invoice.invoice_number[4:] if invoice.invoice_number.startswith('TK25') else invoice.invoice_number,
            'invoice_date': invoice.invoice_date,
            'due_date': invoice.due_date,
            'school_name': invoice.school.name,
            'school_address': invoice.school.address if hasattr(invoice.school, 'address') else '',
            'contact_person': invoice.school.contact_person if hasattr(invoice.school, 'contact_person') else '',
            'school_contact': invoice.school.contact_number if hasattr(invoice.school, 'contact_number') else '',
            'trainers': [],  # Add trainer line items if you have them
            'subtotal': f'{invoice.subtotal:.2f}',
            'taxes': f'{invoice.taxes:.2f}',
            'gst_percent': f'{invoice.gst_percent:.2f}',
            'gst_amount': f'{invoice.gst_amount:.2f}',
            'other_charges': f'{invoice.other_charges:.2f}',
            'discount': f'{invoice.discount:.2f}',
            'paid_amount': f'{invoice.paid_amount:.2f}',
            'total': f'{invoice.total:.2f}',
            'amount_words': '',
            'pay_date': invoice.pay_date,
            'pay_mode': invoice.pay_mode,
            'pay_ref': invoice.pay_ref,
        }
        html = render_to_string('generators/invoice_pdf.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=Invoice_{invoice.invoice_number}.pdf'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('Error generating PDF', status=500)
        return response

admin.site.unregister(Invoice)
admin.site.register(Invoice, InvoiceAdmin)

@admin.register(SalarySlip)
class SalarySlipAdmin(admin.ModelAdmin):
    list_display = ("employee", "month", "year", "net_salary", "payment_date", "download_salary_slip")
    search_fields = ("employee__name", "month", "year")
    list_filter = ("employee", "month", "year")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:salaryslip_id>/download/', self.admin_site.admin_view(self.download_salaryslip_view), name='generators_salaryslip_download'),
        ]
        return custom_urls + urls

    def download_salary_slip(self, obj):
        return format_html('<a class="button" href="{}">Download</a>', f'./{obj.id}/download/')
    download_salary_slip.short_description = 'Download PDF'
    download_salary_slip.allow_tags = True

    def download_salaryslip_view(self, request, salaryslip_id):
        slip = get_object_or_404(SalarySlip, id=salaryslip_id)
        context = {
            'employee_name': slip.employee.name,
            'employee_id': slip.employee.employee_id,
            'designation': slip.employee.designation,
            'date_of_joining': slip.employee.date_of_joining,
            'pan_number': slip.employee.pan_number,
            'month': slip.month,
            'year': slip.year,
            'basic_salary': f'{slip.basic_salary:.2f}',
            'allowances': f'{slip.allowances:.2f}',
            'deductions': f'{slip.deductions:.2f}',
            'net_salary': f'{slip.net_salary:.2f}',
            'total_working_days': slip.total_working_days,
            'days_present': slip.days_present,
            'days_absent': slip.days_absent,
            'overtime_hours': slip.overtime_hours,
            'bank_account': slip.bank_account,
            'payment_date': slip.payment_date,
            'payment_mode': slip.payment_mode,
            'transaction_id': slip.transaction_id,
            'authorized_signatory': slip.authorized_signatory,
        }
        html = render_to_string('generators/salary_slip_pdf.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=SalarySlip_{slip.employee.employee_id}_{slip.month}_{slip.year}.pdf'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('Error generating PDF', status=500)
        return response

admin.site.unregister(SalarySlip)
admin.site.register(SalarySlip, SalarySlipAdmin)

@admin.register(EmployeeAttendance)
class EmployeeAttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "month", "year", "total_present", "created_at")
    search_fields = ("employee__name", "month", "year")
    list_filter = ("employee", "month", "year")
