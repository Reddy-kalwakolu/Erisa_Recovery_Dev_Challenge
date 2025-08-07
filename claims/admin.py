# claims/admin.py

from django.contrib import admin
from .models import Claim, ClaimDetail, Note

# Register your models here.
admin.site.register(Claim)
admin.site.register(ClaimDetail)
admin.site.register(Note)