# claims\admin.py

from django.contrib import admin

from .models import Claim, ClaimDetail, Note, Flag 

# Register models here.
admin.site.register(Claim)
admin.site.register(ClaimDetail)
admin.site.register(Note)

admin.site.register(Flag)
