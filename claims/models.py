# claims\models.py

from django.db import models
from django.contrib.auth.models import User

class Claim(models.Model):
    STATUS_DENIED = 'Denied'
    STATUS_PAID = 'Paid'
    STATUS_UNDER_REVIEW = 'Under Review'
    STATUS_APPEALED = 'Appealed'

    STATUS_CHOICES = [
        (STATUS_DENIED, 'Denied'),
        (STATUS_PAID, 'Paid'),
        (STATUS_UNDER_REVIEW, 'Under Review'),
        (STATUS_APPEALED, 'Appealed'),
    ]

    # Provided Data from CSV/JSON
    claim_id = models.IntegerField(unique=True)
    patient_name = models.CharField(max_length=255)
    billed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default=STATUS_UNDER_REVIEW,
        db_index=True
    )

    insurer_name = models.CharField(max_length=255, db_index=True)
    discharge_date = models.DateField()


    def __str__(self):
        return f"Claim {self.claim_id} - {self.patient_name}"

class ClaimDetail(models.Model):
    claim = models.OneToOneField(Claim, on_delete=models.CASCADE, related_name="details")
    cpt_codes = models.CharField(max_length=255)
    denial_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Details for Claim {self.claim.id}"

class Note(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="notes")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=False)

    def __str__(self):
        return f"Note by {self.user.username} on Claim {self.claim.id}"

    class Meta:
        ordering = ['-created_at']

class ClaimHistory(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="history")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    old_status = models.CharField(max_length=50)
    new_status = models.CharField(max_length=50)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"History for Claim {self.claim.claim_id} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']


# Model to handle user-specific flagging
class Flag(models.Model):
    """Represents a user flagging a claim for review."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flags')
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='flags')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A user can only flag a specific claim once.
        unique_together = ('user', 'claim')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} flagged Claim {self.claim.claim_id}"
