# claims/models.py

from django.db import models
from django.contrib.auth.models import User

# Model for the main claim information
class Claim(models.Model):
    # Provided Data from CSV/JSON
    claim_id = models.IntegerField(unique=True)
    patient_name = models.CharField(max_length=255)
    billed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, db_index=True)
    insurer_name = models.CharField(max_length=255, db_index=True)
    discharge_date = models.DateField()

    # User-Generated Data for flagging
    is_flagged = models.BooleanField(default=False)

    def __str__(self):
        return f"Claim {self.claim_id} - {self.patient_name}"

# Model for the detailed claim data, linked one-to-one with a Claim
class ClaimDetail(models.Model):
    claim = models.OneToOneField(Claim, on_delete=models.CASCADE, related_name="details")
    cpt_codes = models.CharField(max_length=255)
    denial_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Details for Claim {self.claim.id}"

# Model for user notes, linked many-to-one with a Claim
class Note(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="notes")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note by {self.user.username} on Claim {self.claim.id}"