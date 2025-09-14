# claims/views.py

import json
from django.core.paginator import Paginator
from django.db.models import Q, F, Count, Avg, Exists, OuterRef, Sum
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.template.loader import render_to_string
from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView
from django.views.generic.edit import CreateView
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta

from .forms import CustomUserCreationForm
from .models import Claim, ClaimDetail, Note, ClaimHistory, Flag
from .utils import process_claim_data

# def home_view(request):
#     """Renders the public-facing home page for all users."""
#     return render(request, 'claims/home.html')


def home_view(request):
    """
    Renders the internal homepage for authenticated users,
    otherwise redirects to the login page.
    """
    if request.user.is_authenticated:
        return render(request, 'claims/home.html')
    else:
        return redirect('claims:login')

# ... (rest of your views.py file) ...

class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('claims:login')
    template_name = 'claims/register.html'

    def form_valid(self, form):
        messages.success(self.request, "Registration successful! You can now log in.")
        return super().form_valid(form)

@login_required
@require_POST
def flag_claim_view(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    flag, created = Flag.objects.get_or_create(user=request.user, claim=claim)
    if not created:
        flag.delete()
        is_flagged_by_user = False
    else:
        is_flagged_by_user = True
    claim.is_flagged_by_user = is_flagged_by_user
    context = {'claim': claim}
    return render(request, 'claims/partials/_flag_update_response.html', context)

@login_required
def claim_list_view(request):
    user_flags = Flag.objects.filter(claim=OuterRef('pk'), user=request.user)
    claims_list = Claim.objects.select_related('details').prefetch_related('notes', 'history').annotate(
        is_flagged_by_user=Exists(user_flags)
    )

    search_query = request.GET.get('q', '')
    patient_query = request.GET.get('patient_name', '')
    status_query = request.GET.get('status', '')
    insurer_query = request.GET.get('insurer_name', '')

    if search_query:
        claims_list = claims_list.filter(
            Q(patient_name__icontains=search_query) |
            Q(status__icontains=search_query) |
            Q(insurer_name__icontains=search_query)
        )
    if patient_query:
        claims_list = claims_list.filter(patient_name__icontains=patient_query)
    if status_query:
        claims_list = claims_list.filter(status__icontains=status_query)
    if insurer_query:
        claims_list = claims_list.filter(insurer_name__icontains=insurer_query)
    
    claims_list = claims_list.order_by('-discharge_date')

    paginator = Paginator(claims_list, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    if 'show_details_for' in query_params:
        del query_params['show_details_for']

    context = {
        'page_obj': page_obj,
        'query_params': query_params.urlencode(),
        'show_details_for_id': request.GET.get('show_details_for'),
    }

    if request.headers.get('HX-Request') == 'true':
        return render(request, 'claims/partials/_claims_content_partial.html', context)

    return render(request, 'claims/claim_list.html', context)


@login_required
def claim_detail_view(request, pk):
    try:
        claim = Claim.objects.select_related('details').prefetch_related('notes', 'history__user').get(pk=pk)
    except Claim.DoesNotExist:
        raise Http404("Claim does not exist")

    visible_notes = claim.notes.filter(Q(is_public=True) | Q(user=request.user))

    cpt_codes_list = []
    if hasattr(claim, 'details') and claim.details and claim.details.cpt_codes:
        cpt_codes_list = [code.strip() for code in claim.details.cpt_codes.split(',')]

    underpayment_amount = claim.billed_amount - claim.paid_amount
    is_flagged_by_user = claim.flags.filter(user=request.user).exists()

    context = {
        'claim': claim,
        'visible_notes': visible_notes,
        'status_choices': Claim.STATUS_CHOICES,
        'cpt_codes_list': cpt_codes_list,
        'underpayment_amount': underpayment_amount,
        'is_flagged_by_user': is_flagged_by_user,
    }

    details_html = render_to_string('claims/partials/_claim_details_card.html', context, request=request)
    change_status_html = render_to_string('claims/partials/_change_status_card.html', context, request=request)
    analyse_agent_html = render_to_string('claims/partials/_analyse_agent_card.html', context, request=request)
    status_history_html = render_to_string('claims/partials/_status_history_card.html', context, request=request)
    notes_html = render_to_string('claims/partials/_notes_card.html', context, request=request)
    actions_html = render_to_string('claims/partials/_actions_card.html', context, request=request)
    placeholder_idea_html = render_to_string('claims/partials/_placeholder_idea_card.html', context, request=request)

    response_html = f"""
    {details_html}
    <div id="change-status-card" hx-swap-oob="innerHTML">{change_status_html}</div>
    <div id="analyse-agent-card" hx-swap-oob="innerHTML">{analyse_agent_html}</div>
    <div id="status-history-card" hx-swap-oob="innerHTML">{status_history_html}</div>
    <div id="notes-card" hx-swap-oob="innerHTML">{notes_html}</div>
    <div id="actions-card" hx-swap-oob="innerHTML">{actions_html}</div>
    <div id="placeholder-idea-card" hx-swap-oob="innerHTML">{placeholder_idea_html}</div>
    """
    return HttpResponse(response_html)

@login_required
def add_note_view(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    if request.method == 'POST':
        note_text = request.POST.get('note_text', '').strip()
        is_public = request.POST.get('is_public') == 'on'
        if note_text:
            Note.objects.create(
                claim=claim,
                user=request.user,
                text=note_text,
                is_public=is_public
            )
        visible_notes = claim.notes.filter(
            Q(is_public=True) | Q(user=request.user)
        )
        context = {'claim': claim, 'visible_notes': visible_notes}
        return render(request, 'claims/partials/_notes_list_partial.html', context)

@require_POST
@login_required
def delete_note_view(request, pk):
    note = get_object_or_404(Note, pk=pk)
    if request.user != note.user:
        return HttpResponseForbidden("You are not allowed to delete this note.")
    note.delete()
    return HttpResponse("")

@require_POST
@login_required
def edit_note_view(request, pk):
    note = get_object_or_404(Note, pk=pk)
    if request.user != note.user:
        return HttpResponseForbidden("You are not allowed to edit this note.")
    new_text = request.POST.get('note_text', '').strip()
    if new_text:
        note.text = new_text
        note.save()
    context = {'note': note}
    return render(request, 'claims/partials/_note_item_partial.html', context)

@login_required
def change_claim_status_view(request, pk):
    claim = get_object_or_404(Claim.objects.prefetch_related('history__user'), pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        comment = request.POST.get('comment', '')
        old_status = claim.get_status_display()
        if new_status in dict(Claim.STATUS_CHOICES) and new_status != claim.status:
            claim.status = new_status
            claim.save()
            ClaimHistory.objects.create(
                claim=claim,
                user=request.user,
                old_status=old_status,
                new_status=claim.get_status_display(),
                comment=comment
            )

    claim = get_object_or_404(Claim.objects.prefetch_related('history__user'), pk=pk)
    underpayment_amount = claim.billed_amount - claim.paid_amount
    context = {
        'claim': claim,
        'status_choices': Claim.STATUS_CHOICES,
        'underpayment_amount': underpayment_amount,
    }
    return render(request, 'claims/partials/_status_update_response.html', context)

@login_required
def generate_report_view(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    return render(request, 'claims/report_placeholder.html', {'claim': claim})

@login_required
def dashboard_view(request):
    # --- KPI Bar Calculations ---
    total_underpayment = Claim.objects.aggregate(
        total=Sum(F('billed_amount') - F('paid_amount'))
    )['total']

    claims_awaiting_action = Claim.objects.filter(
        Q(status=Claim.STATUS_DENIED) | Q(status=Claim.STATUS_UNDER_REVIEW)
    ).count()

    my_flagged_claims_count = Flag.objects.filter(user=request.user).count()

    average_underpayment = Claim.objects.aggregate(
        avg=Avg(F('billed_amount') - F('paid_amount'))
    )['avg']

    # --- Action Queues Data ---
    high_value_denials = Claim.objects.filter(status=Claim.STATUS_DENIED).annotate(
        underpayment=F('billed_amount') - F('paid_amount')
    ).order_by('-underpayment')[:5]

    aging_claims = Claim.objects.filter(status=Claim.STATUS_UNDER_REVIEW).order_by('discharge_date')[:5]
    
    my_flagged_items = Claim.objects.filter(flags__user=request.user).distinct()[:5]

    # --- System Insights Data ---
    top_denial_reasons = ClaimDetail.objects.filter(denial_reason__isnull=False).exclude(denial_reason__exact='').values(
        'denial_reason'
    ).annotate(
        count=Count('denial_reason')
    ).order_by('-count')[:3]

    recent_activity = ClaimHistory.objects.select_related('claim', 'user').order_by('-timestamp')[:5]

    context = {
        'total_underpayment': total_underpayment,
        'claims_awaiting_action': claims_awaiting_action,
        'my_flagged_claims_count': my_flagged_claims_count,
        'average_underpayment': average_underpayment,
        'high_value_denials': high_value_denials,
        'aging_claims': aging_claims,
        'my_flagged_items': my_flagged_items,
        'top_denial_reasons': top_denial_reasons,
        'recent_activity': recent_activity,
    }
    return render(request, 'claims/dashboard.html', context)


@login_required
def upload_claims_view(request):
    if request.method == 'POST':
        claims_file = request.FILES.get('claims_file')
        details_file = request.FILES.get('details_file')
        mode = request.POST.get('mode')

        if not all([claims_file, details_file, mode]):
            messages.error(request, 'Please provide both files and select an upload mode.')
            return redirect('claims:upload-claims')

        try:
            claims_data = json.loads(claims_file.read().decode('utf-8'))
            details_data = json.loads(details_file.read().decode('utf-8'))

            claims_created, claims_updated, details_created, details_updated = process_claim_data(
                claims_data, details_data, mode
            )

            messages.success(request,
                f'Upload successful! Claims: {claims_created} created, {claims_updated} updated. '
                f'Details: {details_created} created, {details_updated} updated.'
            )
            return redirect('claims:dashboard')

        except json.JSONDecodeError:
            messages.error(request, 'Upload failed. One of the files is not valid JSON.')
            return redirect('claims:upload-claims')
        except KeyError as e:
            messages.error(request, f'Upload failed. A required key is missing from the data: {e}')
            return redirect('claims:upload-claims')
        except Exception as e:
            messages.error(request, f'An unexpected error occurred: {e}')
            return redirect('claims:upload-claims')

    return render(request, 'claims/upload_claims.html')