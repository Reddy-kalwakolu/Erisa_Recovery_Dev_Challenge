# claims/utils.py

import json
from .models import Claim, ClaimDetail

def process_claim_data(claims_data, details_data, mode):
    """
    Processes and loads claim data into the database.
    
    :param claims_data: A list of dictionaries for claims.
    :param details_data: A list of dictionaries for claim details.
    :param mode: 'overwrite' or 'append'.
    :return: A tuple of (claims_created, claims_updated, details_created, details_updated)
    """
    
    if mode == 'overwrite':
        # If overwriting, delete all existing data first
        Claim.objects.all().delete()
        # ClaimDetail and Note records are deleted automatically due to CASCADE.

    claims_created = 0
    claims_updated = 0
    details_created = 0
    details_updated = 0

    # --- Process Claims ---
    for claim_data in claims_data:
        obj, created = Claim.objects.update_or_create(
            claim_id=claim_data['id'],
            defaults={
                'patient_name': claim_data['patient_name'],
                'billed_amount': claim_data['billed_amount'],
                'paid_amount': claim_data['paid_amount'],
                'status': claim_data['status'],
                'insurer_name': claim_data['insurer_name'],
                'discharge_date': claim_data['discharge_date'],
            }
        )
        if created:
            claims_created += 1
        else:
            claims_updated += 1
    
    # --- Process Claim Details ---
    for detail_data in details_data:
        try:
            parent_claim = Claim.objects.get(claim_id=detail_data['claim_id'])
            obj, created = ClaimDetail.objects.update_or_create(
                claim=parent_claim,
                defaults={
                    'denial_reason': detail_data['denial_reason'],
                    'cpt_codes': detail_data['cpt_codes'],
                }
            )
            if created:
                details_created += 1
            else:
                details_updated += 1
        except Claim.DoesNotExist:
            continue
            
    return (claims_created, claims_updated, details_created, details_updated)