
# claims/views.py

from django.core.paginator import Paginator # 1. Import Paginator
from django.db.models import Q # <-- Add this line
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import Claim, ClaimDetail, Note
from django.db.models import Count, Avg, F
from django.shortcuts import render, redirect
from django.contrib import messages # Import Django's messaging framework
from django.contrib.auth.decorators import login_required
from .utils import process_claim_data
# Replace your old claim_list_view with this one

# claims/views.py

def claim_list_view(request):
    # ... (all the query and pagination logic is the same)
    query = request.GET.get('q', '')
    claims_list = Claim.objects.all()
    if query:
        claims_list = claims_list.filter(
            Q(status__icontains=query) | Q(insurer_name__icontains=query)
        ).distinct()
    claims_list = claims_list.order_by('-discharge_date')
    paginator = Paginator(claims_list, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }

    if request.htmx:
        # UPDATE THIS FILENAME
        return render(request, 'claims/partials/_claims_content_partial.html', context)
    
    return render(request, 'claims/claim_list.html', context)


def claim_detail_view(request, pk):
    # Get the specific claim object, or return a 404 error if not found
    claim = get_object_or_404(Claim, pk=pk)
    
    context = {
        'claim': claim
    }
    
    # Render the PARTIAL template and return it
    return render(request, 'claims/partials/_claim_detail_partial.html', context)

def flag_claim_view(request, pk):
    # We only accept POST requests for this view
    if request.method == 'POST':
        claim = get_object_or_404(Claim, pk=pk)
        
        # Flip the boolean value of is_flagged
        claim.is_flagged = not claim.is_flagged
        claim.save()

        # Return the updated button partial to HTMX
        context = {'claim': claim}
        return render(request, 'claims/partials/_flag_button_partial.html', context)
    


@login_required
def add_note_view(request, pk):
    if request.method == 'POST':
        claim = get_object_or_404(Claim, pk=pk)
        note_text = request.POST.get('note_text')

        if note_text:
            Note.objects.create(
                claim=claim,
                user=request.user,
                text=note_text
            )
        
        # Return the updated list of notes to HTMX
        context = {'claim': claim}
        return render(request, 'claims/partials/_notes_list_partial.html', context)
    
# Add this entire function to claims/views.py

def dashboard_view(request):
    # Calculate the total number of claims that are flagged
    total_flagged_claims = Claim.objects.filter(is_flagged=True).count()

    # Calculate the average difference between what was billed and what was paid
    underpayment_stats = Claim.objects.aggregate(
        average_underpayment=Avg(F('billed_amount') - F('paid_amount'))
    )

    context = {
        'total_flagged_claims': total_flagged_claims,
        'average_underpayment': underpayment_stats['average_underpayment'],
    }

    return render(request, 'claims/dashboard.html', context)
@login_required
def upload_claims_view(request):
    if request.method == 'POST':
        claims_file = request.FILES.get('claims_file')
        details_file = request.FILES.get('details_file')
        mode = request.POST.get('mode')

        # Basic validation
        if not claims_file or not details_file or not mode:
            messages.error(request, 'Please provide both files and select an upload mode.')
            return redirect('claims:upload-claims')
        
        try:
            # Read and parse the in-memory files
            claims_data = json.loads(claims_file.read().decode('utf-8'))
            details_data = json.loads(details_file.read().decode('utf-8'))

            # Call our utility function to process the data
            claims_created, claims_updated, details_created, details_updated = process_claim_data(
                claims_data,
                details_data,
                mode
            )
            
            # Create a success message
            messages.success(request, 
                f'Upload successful! Claims: {claims_created} created, {claims_updated} updated. '
                f'Details: {details_created} created, {details_updated} updated.'
            )
            return redirect('claims:dashboard') # Redirect to dashboard to see updated stats

        except Exception as e:
            messages.error(request, f'An error occurred: {e}')
            return redirect('claims:upload-claims')

    return render(request, 'claims/upload_claims.html')