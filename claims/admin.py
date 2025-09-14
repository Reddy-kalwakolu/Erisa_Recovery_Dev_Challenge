# C:\Users\Kcpre\OneDrive\Desktop\Erisa_Recovery_Dev_Challenge - Copy\claims\admin.py

from django.contrib import admin
# ======================================= #
# START OF FIX
from .models import Claim, ClaimDetail, Note, Flag # Import the new Flag model
# END OF FIX
# ======================================= #

# Register your models here.
admin.site.register(Claim)
admin.site.register(ClaimDetail)
admin.site.register(Note)
# ======================================= #
# START OF FIX
admin.site.register(Flag) # Register the Flag model
# END OF FIX
# ======================================= #