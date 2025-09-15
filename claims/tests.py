# path: claims/tests.py


from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import IntegrityError
from django.core.files.uploadedfile import SimpleUploadedFile
import json
from io import StringIO
from django.core.management import call_command

from .models import Claim, ClaimDetail, Note, Flag, ClaimHistory
from .utils import process_claim_data
from .forms import CustomUserCreationForm

# ================================================================= #
# 1. MODEL TESTS
# ================================================================= #
class ModelTests(TestCase):
    """
    Tests to ensure models are created correctly, relationships are sound,
    and database constraints are enforced.
    """
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.claim = Claim.objects.create(
            claim_id=101, patient_name='John Doe', billed_amount=1000.00,
            paid_amount=800.00, status='Paid', insurer_name='Test Insurer',
            discharge_date='2025-01-01'
        )

    def test_claim_model_str(self):
        """Verifies the string representation of the Claim model."""
        self.assertEqual(str(self.claim), 'Claim 101 - John Doe')

    def test_note_creation_and_relationship(self):
        """Verifies a Note can be created and is correctly linked to a User and Claim."""
        note = Note.objects.create(user=self.user, claim=self.claim, text='Test note.')
        self.assertEqual(str(note), f'Note by testuser on Claim {self.claim.id}')
        self.assertEqual(self.claim.notes.count(), 1)
        self.assertEqual(self.user.note_set.first(), note)

    def test_flag_uniqueness_constraint(self):
        """EDGE CASE: Verifies that a user cannot flag the same claim twice."""
        Flag.objects.create(user=self.user, claim=self.claim)
        self.assertEqual(self.claim.flags.count(), 1)
        # Verifies the `unique_together` constraint on the Flag model
        with self.assertRaises(IntegrityError):
            Flag.objects.create(user=self.user, claim=self.claim)

    def test_cascade_delete_on_claim(self):
        """EDGE CASE: Verifies that deleting a Claim also deletes its related Notes, Flags, etc."""
        ClaimDetail.objects.create(claim=self.claim, cpt_codes='123', denial_reason='Test')
        Note.objects.create(user=self.user, claim=self.claim, text='A note')
        Flag.objects.create(user=self.user, claim=self.claim)
        ClaimHistory.objects.create(claim=self.claim, old_status='A', new_status='B')

        self.claim.delete()

        self.assertEqual(Claim.objects.count(), 0)
        self.assertEqual(ClaimDetail.objects.count(), 0)
        self.assertEqual(Note.objects.count(), 0)
        self.assertEqual(Flag.objects.count(), 0)
        self.assertEqual(ClaimHistory.objects.count(), 0)

# ================================================================= #
# 2. UTILS TESTS (CORE BUSINESS LOGIC) - EXPANDED
# ================================================================= #
class UtilsTests(TestCase):
    """
    Tests the core data ingestion logic in `utils.py`, which is used by both
    the management command and the file upload view for both JSON and CSV.
    """
    def setUp(self):
        # JSON Data
        self.claims_data_json = [{"id": "30001", "patient_name": "Jane Doe", "billed_amount": 100, "paid_amount": 50, "status": "Denied", "insurer_name": "InsureCo", "discharge_date": "2025-01-01"}]
        self.details_data_json = [{"id": "1", "claim_id": "30001", "denial_reason": "Policy ended", "cpt_codes": "99204"}]
        # CSV Data
        self.claims_data_csv = [
            {'id': '30002', 'patient_name': 'John Smith', 'billed_amount': '250.75', 'paid_amount': '200.00', 'status': 'Paid', 'insurer_name': 'HealthCorp', 'discharge_date': '2025-02-15'}
        ]
        self.details_data_csv = [
            {'id': '2', 'claim_id': '30002', 'denial_reason': '', 'cpt_codes': '99213,90834'}
        ]

    def test_process_data_append_mode_json(self):
        """Verifies 'append' mode creates and updates records from JSON data."""
        stats = process_claim_data(self.claims_data_json, self.details_data_json, 'append')
        self.assertEqual(stats, (1, 0, 1, 0)) # 1 claim created, 1 detail created

        updated_claims_data = [{"id": "30001", "patient_name": "Jane Smith", "billed_amount": 120, "paid_amount": 60, "status": "Paid", "insurer_name": "InsureCo", "discharge_date": "2025-01-01"}]
        stats_update = process_claim_data(updated_claims_data, self.details_data_json, 'append')
        self.assertEqual(stats_update, (0, 1, 0, 1)) # 1 claim updated, 1 detail updated
        self.assertEqual(Claim.objects.first().patient_name, "Jane Smith")

    def test_process_data_append_mode_csv(self):
        """Verifies 'append' mode creates records correctly from CSV data."""
        stats = process_claim_data(self.claims_data_csv, self.details_data_csv, 'append')
        self.assertEqual(stats, (1, 0, 1, 0))
        self.assertEqual(Claim.objects.count(), 1)
        claim = Claim.objects.first()
        self.assertEqual(claim.patient_name, "John Smith")
        self.assertEqual(claim.billed_amount, 250.75)

    def test_process_data_overwrite_mode(self):
        """Verifies 'overwrite' mode deletes all old data before inserting."""
        Claim.objects.create(claim_id=999, patient_name='Old Claim', billed_amount=1, paid_amount=1, status='Paid', insurer_name='Old Insurer', discharge_date='2025-01-01')
        process_claim_data(self.claims_data_json, self.details_data_json, 'overwrite')
        self.assertEqual(Claim.objects.count(), 1)
        self.assertFalse(Claim.objects.filter(claim_id=999).exists())

    def test_process_data_handles_missing_key(self):
        """EDGE CASE: Verifies that the function raises a KeyError if data is malformed."""
        bad_claims_data = [{"id": 30002}] # Missing 'patient_name', etc.
        with self.assertRaises(KeyError):
            process_claim_data(bad_claims_data, self.details_data_json, 'append')

    def test_process_data_handles_claim_without_detail(self):
        """EDGE CASE: Verifies the process doesn't fail if a detail record points to a non-existent claim."""
        bad_details_data = [{"id": 2, "claim_id": 99999, "denial_reason": "No claim", "cpt_codes": "123"}]
        stats = process_claim_data(self.claims_data_json, bad_details_data, 'append')
        self.assertEqual(stats, (1, 0, 0, 0))

# ================================================================= #
# 3. REGISTRATION AND LOGIN TESTS
# ================================================================= #
class RegistrationAndLoginTests(TestCase):
    """Tests all user authentication features, including custom form validation."""
    def setUp(self):
        self.user = User.objects.create_user(username='existinguser', password='password123', email='exists@example.com')

    def test_registration_duplicate_username(self):
        """EDGE CASE: Verifies that a user cannot register with an existing username."""
        form = CustomUserCreationForm(data={'username': 'existinguser', 'email': 'new@example.com'})
        self.assertFalse(form.is_valid())
        self.assertIn('A user with that username already exists.', form.errors['username'])

    def test_registration_duplicate_email(self):
        """EDGE CASE: Verifies our custom validation for unique emails works."""
        form = CustomUserCreationForm(data={'username': 'newuser', 'email': 'exists@example.com'})
        self.assertFalse(form.is_valid())
        self.assertIn('An account with this email address already exists.', form.errors['email'])

    def test_successful_login_and_logout(self):
        """FUNCTIONALITY: Verifies a user can successfully log in and log out."""
        response = self.client.post(reverse('claims:login'), {'username': 'existinguser', 'password': 'password123'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'claims/claim_list.html')
        self.assertTrue(response.context['user'].is_authenticated)

        response = self.client.get(reverse('claims:logout'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'claims/login.html')
        self.assertFalse(response.context['user'].is_authenticated)

    def test_failed_login(self):
        """EDGE CASE: Verifies that a failed login attempt shows an error."""
        response = self.client.post(reverse('claims:login'), {'username': 'existinguser', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'claims/login.html')
        self.assertContains(response, 'Please enter a correct username and password.')
        self.assertFalse(response.context['user'].is_authenticated)

# ================================================================= #
# 4. VIEW TESTS (Expanded)
# ================================================================= #
class ViewTests(TestCase):
    """
    Tests all views for security (authentication/authorization), correct functionality,
    and graceful handling of edge cases.
    """
    def setUp(self):
        self.user_a = User.objects.create_user(username='user_a', password='password123')
        self.user_b = User.objects.create_user(username='user_b', password='password123')
        self.client_a = Client()
        self.client_a.login(username='user_a', password='password123')
        self.claim1 = Claim.objects.create(claim_id=1, patient_name='Patient Alpha', status='Denied', insurer_name='InsureCo', billed_amount=1000, paid_amount=0, discharge_date='2025-01-01')
        self.claim2 = Claim.objects.create(claim_id=2, patient_name='Patient Bravo', status='Paid', insurer_name='HealthCo', billed_amount=500, paid_amount=500, discharge_date='2025-01-02')
        self.note_private_by_a = Note.objects.create(user=self.user_a, claim=self.claim1, text='Private note by A', is_public=False)
        self.note_public_by_a = Note.objects.create(user=self.user_a, claim=self.claim1, text='Public note by A', is_public=True)

    def test_unauthenticated_access_is_redirected(self):
        """SECURITY: Verifies that anonymous users are redirected from all protected views."""
        unauthenticated_client = Client()
        protected_urls = [
            reverse('claims:dashboard'),
            reverse('claims:claim-list'),
            reverse('claims:upload-claims'),
            reverse('claims:claim-detail', kwargs={'pk': self.claim1.pk}),
        ]
        for url in protected_urls:
            response = unauthenticated_client.get(url)
            self.assertEqual(response.status_code, 302, f"URL {url} did not redirect.")
            self.assertIn(reverse('claims:login'), response.url, f"URL {url} did not redirect to the login page.")

    def test_user_cannot_delete_another_users_note(self):
        """SECURITY: Verifies a 403 Forbidden error when a user tries to delete another's note."""
        client_b = Client()
        client_b.login(username='user_b', password='password123')
        delete_url = reverse('claims:delete-note', kwargs={'pk': self.note_public_by_a.pk})
        response = client_b.post(delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Note.objects.filter(pk=self.note_public_by_a.pk).exists(), "Note was deleted when it should not have been.")

    def test_user_cannot_edit_another_users_note(self):
        """SECURITY: Verifies a 403 Forbidden error when a user tries to edit another's note."""
        client_b = Client()
        client_b.login(username='user_b', password='password123')
        edit_url = reverse('claims:edit-note', kwargs={'pk': self.note_public_by_a.pk})
        response = client_b.post(edit_url, {'note_text': 'Hacked by B'})
        self.assertEqual(response.status_code, 403)
        self.note_public_by_a.refresh_from_db()
        self.assertNotEqual(self.note_public_by_a.text, 'Hacked by B', "Note was edited when it should not have been.")

    def test_note_visibility_for_different_users(self):
        """SECURITY: Verifies user_b can see user_a's public note but not their private note."""
        client_b = Client()
        client_b.login(username='user_b', password='password123')
        response = client_b.get(reverse('claims:claim-detail', kwargs={'pk': self.claim1.pk}))
        self.assertContains(response, 'Public note by A')
        self.assertNotContains(response, 'Private note by A')

    def test_add_note_handles_empty_submission(self):
        """EDGE CASE: Verifies that submitting an empty note does not create a new Note object."""
        add_note_url = reverse('claims:add-note', kwargs={'pk': self.claim1.pk})
        note_count_before = Note.objects.count()
        self.client_a.post(add_note_url, {'note_text': '   '})
        note_count_after = Note.objects.count()
        self.assertEqual(note_count_before, note_count_after)

    def test_claim_list_search(self):
        """FUNCTIONALITY: Verifies the search and filter functionality on the main list view."""
        response = self.client_a.get(reverse('claims:claim-list'), {'patient_name': 'Alpha'})
        self.assertContains(response, 'Patient Alpha')
        self.assertNotContains(response, 'Patient Bravo')

    def test_pagination_works(self):
        """FUNCTIONALITY: Verifies that pagination on the claims list page works."""
        for i in range(3, 7):
            Claim.objects.create(claim_id=i, patient_name=f'Patient {i}', status='Denied', insurer_name='InsureCo', billed_amount=100, paid_amount=0, discharge_date='2025-01-01')
        self.assertEqual(Claim.objects.count(), 6)
        response = self.client_a.get(reverse('claims:claim-list') + '?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Patient Alpha') # on page 1
        
        claims_list = Claim.objects.all().order_by('-discharge_date') # 6 total items
        # claim2, claim1, P3, P4, P5, P6
        response_page_2 = self.client_a.get(reverse('claims:claim-list') + '?page=2')
        self.assertEqual(response_page_2.status_code, 200)
        self.assertNotContains(response_page_2, 'Patient Bravo') # on page 1
        self.assertContains(response_page_2, 'Patient 6') # on page 2
        
    # ======================================= #
    # START OF NEW TESTS FOR CSV UPLOAD
    # ======================================= #
    def test_upload_view_with_csv(self):
        """FUNCTIONALITY: Verifies the upload view can process valid CSV files."""
        self.client_a.login(username='user_a', password='password123')

        claims_csv_content = "id,patient_name,billed_amount,paid_amount,status,insurer_name,discharge_date\n40001,CSV Patient,500.00,400.00,Paid,CSV Insurer,2025-03-01"
        details_csv_content = "id,claim_id,denial_reason,cpt_codes\n1,40001,,99215"

        claims_file = SimpleUploadedFile("claims.csv", claims_csv_content.encode('utf-8'), content_type="text/csv")
        details_file = SimpleUploadedFile("details.csv", details_csv_content.encode('utf-8'), content_type="text/csv")

        upload_url = reverse('claims:upload-claims')
        response = self.client_a.post(upload_url, {
            'claims_file': claims_file,
            'details_file': details_file,
            'mode': 'overwrite'
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'claims/dashboard.html')
        self.assertContains(response, "Upload successful! Claims: 1 created")
        self.assertTrue(Claim.objects.filter(claim_id=40001).exists())
    # ======================================= #
    # END OF NEW TESTS
    # ======================================= #

    
    def test_unauthenticated_post_to_upload_is_redirected(self):
        """SECURITY: Verifies unauthenticated POST to upload view is redirected to login."""
        unauthenticated_client = Client()
        upload_url = reverse('claims:upload-claims')
        response = unauthenticated_client.post(upload_url, {})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('claims:login'), response.url)


# ================================================================= #
# 5. MANAGEMENT COMMAND TESTS
# ================================================================= #
class ManagementCommandTests(TestCase):
    """
    Tests the custom `load_claims` management command to ensure it runs
    correctly and handles arguments properly for both JSON and CSV.
    """
    def tearDown(self):
        import os
        files_to_remove = ['test_claims.json', 'test_details.json', 'test_claims.csv', 'test_details.csv']
        for f in files_to_remove:
            if os.path.exists(f):
                os.remove(f)

    def test_load_claims_command_json(self):
        """FUNCTIONALITY: Verifies the management command successfully loads JSON data."""
        claims_data = '[{"id": 30001, "patient_name": "Test Patient", "billed_amount": 100, "paid_amount": 50, "status": "Denied", "insurer_name": "InsureCo", "discharge_date": "2025-01-01"}]'
        details_data = '[{"id": 1, "claim_id": 30001, "denial_reason": "Test reason", "cpt_codes": "99204"}]'
        with open('test_claims.json', 'w') as f: f.write(claims_data)
        with open('test_details.json', 'w') as f: f.write(details_data)
        out = StringIO()
        call_command('load_claims', 'test_claims.json', 'test_details.json', '--mode=overwrite', stdout=out)
        self.assertIn('Processing complete. Claims: 1 created, 0 updated.', out.getvalue())
        self.assertEqual(Claim.objects.count(), 1)

    def test_load_claims_command_csv(self):
        """FUNCTIONALITY: Verifies the management command successfully loads CSV data."""
        claims_csv_content = "id,patient_name,billed_amount,paid_amount,status,insurer_name,discharge_date\n40001,CSV Patient,500.00,400.00,Paid,CSV Insurer,2025-03-01"
        details_csv_content = "id,claim_id,denial_reason,cpt_codes\n1,40001,,99215"
        with open('test_claims.csv', 'w') as f: f.write(claims_csv_content)
        with open('test_details.csv', 'w') as f: f.write(details_csv_content)
        out = StringIO()
        call_command('load_claims', 'test_claims.csv', 'test_details.csv', '--mode=overwrite', stdout=out)
        self.assertIn('Processing complete. Claims: 1 created, 0 updated.', out.getvalue())
        self.assertEqual(Claim.objects.count(), 1)
        self.assertTrue(Claim.objects.filter(claim_id=40001).exists())