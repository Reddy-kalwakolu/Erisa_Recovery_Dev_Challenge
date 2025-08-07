# claims/management/commands/load_claims.py

import json
from django.core.management.base import BaseCommand
from claims.utils import process_claim_data # <-- Import our new function

class Command(BaseCommand):
    help = 'Loads claims and claim details from specified JSON files'

    def add_arguments(self, parser):
        parser.add_argument('claims_file_path', type=str, help='The path to the claims JSON file.')
        parser.add_argument('details_file_path', type=str, help='The path to the claim details JSON file.')
        parser.add_argument(
            '--mode',
            type=str,
            help="'overwrite' or 'append'",
            default='append' # Default to the safer 'append' mode
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data loading process...'))

        # Load data from files
        with open(options['claims_file_path'], 'r') as f:
            claims_data = json.load(f)
        
        with open(options['details_file_path'], 'r') as f:
            details_data = json.load(f)
        
        # Call the shared processing function
        claims_created, claims_updated, details_created, details_updated = process_claim_data(
            claims_data,
            details_data,
            options['mode']
        )

        self.stdout.write(self.style.SUCCESS(
            f'Processing complete. Claims: {claims_created} created, {claims_updated} updated. '
            f'Details: {details_created} created, {details_updated} updated.'
        ))