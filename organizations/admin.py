from django.contrib import admin

from organizations.models import District, Ministry, School

admin.site.register(Ministry)
admin.site.register(District)
admin.site.register(School)
