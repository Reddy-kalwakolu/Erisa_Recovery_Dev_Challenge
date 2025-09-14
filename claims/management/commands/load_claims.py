# claims/management/commands/load_claims.py

from django.core.management.base import BaseCommand
from claims.utils import parse_data_from_stream, process_claim_data

class Command(BaseCommand):
    help = 'Loads claims and claim details from specified JSON or CSV files'

    def add_arguments(self, parser):
        parser.add_argument('claims_file_path', type=str, help='The path to the claims data file (.json or .csv).')
        parser.add_argument('details_file_path', type=str, help='The path to the claim details data file (.json or .csv).')
        parser.add_argument(
            '--mode',
            type=str,
            help="'overwrite' or 'append'",
            default='append'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data loading process...'))
        
        claims_file_path = options['claims_file_path']
        details_file_path = options['details_file_path']
        mode = options['mode']

        try:
            # Read and parse claims data
            with open(claims_file_path, 'rb') as f_claims:
                claims_data = parse_data_from_stream(f_claims, claims_file_path)
            
            # Read and parse details data
            with open(details_file_path, 'rb') as f_details:
                details_data = parse_data_from_stream(f_details, details_file_path)

        except FileNotFoundError as e:
            self.stdout.write(self.style.ERROR(f'Error: File not found. {e}'))
            return
        except ValueError as e:
            self.stdout.write(self.style.ERROR(f'Error processing file: {e}'))
            return

        # Call the shared processing function
        claims_created, claims_updated, details_created, details_updated = process_claim_data(
            claims_data,
            details_data,
            mode
        )

        self.stdout.write(self.style.SUCCESS(
            f'Processing complete. Claims: {claims_created} created, {claims_updated} updated. '
            f'Details: {details_created} created, {details_updated} updated.'
        ))