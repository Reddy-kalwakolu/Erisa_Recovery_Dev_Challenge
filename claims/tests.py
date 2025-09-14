# C:\Users\Kcpre\OneDrive\Desktop\Erisa_Recovery_Dev_Challenge - Copy\claims\tests.py

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import IntegrityError

from .models import Claim, ClaimDetail, Note, Flag, ClaimHistory
from .utils import process_claim_data

# ================================================================= #
# 1. MODEL TESTS
# ================================================================= #
class ModelTests(TestCase):
    """
    Tests to ensure models are created correctly, relationships are sound,
    and constraints are enforced.
    """
    def setUp(self):
        self.user_a = User.objects.create_user(username='user_a', password='password123')
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
        note = Note.objects.create(user=self.user_a, claim=self.claim, text='Test note.')
        self.assertEqual(str(note), f'Note by user_a on Claim {self.claim.id}')
        self.assertEqual(self.claim.notes.count(), 1)
        self.assertEqual(self.user_a.note_set.first(), note)

    def test_flag_creation_and_uniqueness_constraint(self):
        """Verifies a Flag can be created and that a user cannot flag the same claim twice."""
        Flag.objects.create(user=self.user_a, claim=self.claim)
        self.assertEqual(self.claim.flags.count(), 1)
        # Verifies the `unique_together` constraint on the Flag model
        with self.assertRaises(IntegrityError):
            Flag.objects.create(user=self.user_a, claim=self.claim)

# ================================================================= #
# 2. UTILS TESTS (CORE BUSINESS LOGIC)
# ================================================================= #
class ProcessClaimDataUtilTests(TestCase):
    """
    Tests the core data ingestion logic, including edge cases and error handling.
    """
    def setUp(self):
        self.claims_data = [{"id": 30001, "patient_name": "Virginia Rhodes", "billed_amount": 100, "paid_amount": 50, "status": "Denied", "insurer_name": "United Healthcare", "discharge_date": "2022-12-19"}]
        self.details_data = [{"id": 1, "claim_id": 30001, "denial_reason": "Policy terminated", "cpt_codes": "99204"}]

    def test_process_data_append_mode(self):
        """Verifies 'append' mode creates new records and then updates them on a second run."""
        # First run should create records
        stats = process_claim_data(self.claims_data, self.details_data, 'append')
        self.assertEqual(stats, (1, 0, 1, 0)) # (claims_created, claims_updated, details_created, details_updated)
        
        # Second run should update the same records
        stats = process_claim_data(self.claims_data, self.details_data, 'append')
        self.assertEqual(stats, (0, 1, 0, 1))

    def test_process_data_overwrite_mode(self):
        """Verifies 'overwrite' mode deletes all old data before inserting."""
        Claim.objects.create(claim_id=999, patient_name='Old Claim', billed_amount=1, paid_amount=1, status='Paid', insurer_name='Old Insurer', discharge_date='2025-01-01')
        self.assertEqual(Claim.objects.count(), 1)
        
        process_claim_data(self.claims_data, self.details_data, 'overwrite')
        
        self.assertEqual(Claim.objects.count(), 1)
        self.assertFalse(Claim.objects.filter(claim_id=999).exists())

    def test_process_data_handles_missing_key(self):
        """Verifies that the function raises a KeyError if data is malformed."""
        bad_claims_data = [{"id": 30002, "patient_name": "Missing Data"}] # Missing billed_amount, etc.
        with self.assertRaises(KeyError):
            process_claim_data(bad_claims_data, self.details_data, 'append')

# ================================================================= #
# 3. VIEW TESTS (SECURITY, FUNCTIONALITY, AND EDGE CASES)
# ================================================================= #
class ViewTests(TestCase):
    """
    Tests all views for security, correct functionality, and graceful handling of edge cases.
    """
    def setUp(self):
        self.user_a = User.objects.create_user(username='user_a', password='password123')
        self.user_b = User.objects.create_user(username='user_b', password='password123')
        self.client_a = Client()
        self.client_a.login(username='user_a', password='password123')
        
        self.claim = Claim.objects.create(claim_id=1, patient_name='Test Patient', billed_amount=100, paid_amount=50, status='Denied', insurer_name='InsureCo', discharge_date='2025-01-01')
        self.note_by_a = Note.objects.create(user=self.user_a, claim=self.claim, text='Note by A')

    def test_unauthenticated_access_is_redirected(self):
        """Verifies that anonymous users are redirected from all protected views."""
        unauthenticated_client = Client()
        protected_urls = [
            reverse('claims:claim-list'),
            reverse('claims:dashboard'),
            reverse('claims:claim-detail', kwargs={'pk': self.claim.pk}),
        ]
        for url in protected_urls:
            response = unauthenticated_client.get(url)
            self.assertEqual(response.status_code, 302, f"URL {url} did not redirect.")
            self.assertIn(reverse('claims:login'), response.url)

    def test_user_cannot_delete_another_users_note(self):
        """SECURITY: Verifies that a user receives a 403 Forbidden error when trying to delete another user's note."""
        client_b = Client()
        client_b.login(username='user_b', password='password123')
        delete_url = reverse('claims:delete-note', kwargs={'pk': self.note_by_a.pk})
        
        response = client_b.post(delete_url)
        
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Note.objects.filter(pk=self.note_by_a.pk).exists()) # Ensure note was NOT deleted

    def test_user_cannot_edit_another_users_note(self):
        """SECURITY: Verifies a 403 Forbidden error when a user tries to edit another user's note."""
        client_b = Client()
        client_b.login(username='user_b', password='password123')
        edit_url = reverse('claims:edit-note', kwargs={'pk': self.note_by_a.pk})
        
        response = client_b.post(edit_url, {'note_text': 'Hacked by B'})

        self.assertEqual(response.status_code, 403)
        self.note_by_a.refresh_from_db()
        self.assertNotEqual(self.note_by_a.text, 'Hacked by B') # Ensure note was NOT edited

    def test_add_note_view_handles_empty_submission(self):
        """EDGE CASE: Verifies that submitting an empty note does not create a new Note object."""
        add_note_url = reverse('claims:add-note', kwargs={'pk': self.claim.pk})
        note_count_before = Note.objects.count()
        
        self.client_a.post(add_note_url, {'note_text': '   '}) # Submit with only whitespace
        
        note_count_after = Note.objects.count()
        self.assertEqual(note_count_before, note_count_after)

    def test_htmx_request_receives_partial_template(self):
        """Verifies that a view returns a partial template for HTMX requests."""
        response = self.client_a.get(
            reverse('claims:claim-list'),
            HTTP_HX_REQUEST=True # This header identifies the request as coming from HTMX
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'claims/partials/_claims_content_partial.html')
        self.assertNotContains(response, '<html>') # A partial should not contain the base layout

    def test_browser_request_receives_full_template(self):
        """Verifies that a normal browser request receives the full base template."""
        response = self.client_a.get(reverse('claims:claim-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'claims/claim_list.html')
        self.assertContains(response, '<!DOCTYPE html>') # Check for the doctype declaration