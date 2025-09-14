
# claims/utils.py

import json
import csv
import io
from decimal import Decimal, InvalidOperation
from .models import Claim, ClaimDetail

def parse_data_from_stream(file_stream, filename):
    """
    Parses data from a file stream (CSV or JSON) into a list of dictionaries.

    :param file_stream: An open file-like object.
    :param filename: The name of the file, used to determine the format.
    :return: A list of dictionaries representing the data.
    :raises ValueError: If the file format is unsupported or data is malformed.
    """
    filename = filename.lower()
    
    if filename.endswith('.json'):
        try:
            # Decode the stream from bytes if necessary, then load JSON
            decoded_stream = file_stream.read().decode('utf-8')
            return json.loads(decoded_stream)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON file: {e}")

    elif filename.endswith('.csv'):
        try:
            # Decode and wrap in a StringIO to be read by csv.DictReader
            decoded_stream = io.StringIO(file_stream.read().decode('utf-8'))
            reader = csv.DictReader(decoded_stream)
            # Convert reader object to a list of dictionaries
            return [row for row in reader]
        except Exception as e:
            raise ValueError(f"Error parsing CSV file: {e}")
            
    else:
        raise ValueError("Unsupported file format. Please use .json or .csv")


def process_claim_data(claims_data, details_data, mode):
    """
    Processes and loads claim data into the database from parsed data.

    :param claims_data: A list of dictionaries for claims.
    :param details_data: A list of dictionaries for claim details.
    :param mode: 'overwrite' or 'append'.
    :return: A tuple of (claims_created, claims_updated, details_created, details_updated)
    """
    if mode == 'overwrite':
        Claim.objects.all().delete()

    claims_created = 0
    claims_updated = 0
    details_created = 0
    details_updated = 0

    # --- Process Claims ---
    for claim_data in claims_data:
        try:
            # Ensure amounts are correctly converted to Decimal
            billed_amount = Decimal(claim_data.get('billed_amount', 0))
            paid_amount = Decimal(claim_data.get('paid_amount', 0))
        except (InvalidOperation, TypeError):
            # Skip this record if amount conversion fails
            continue

        obj, created = Claim.objects.update_or_create(
            claim_id=claim_data['id'],
            defaults={
                'patient_name': claim_data['patient_name'],
                'billed_amount': billed_amount,
                'paid_amount': paid_amount,
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
        except KeyError as e:
            # Skip if a required key is missing in the detail data
            print(f"Skipping detail record due to missing key: {e}")
            continue

    return (claims_created, claims_updated, details_created, details_updated)