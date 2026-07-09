from django.contrib import admin
from .models import EntryLog


@admin.register(EntryLog)
class EntryLogAdmin(admin.ModelAdmin):
    list_display = ('ticket_code', 'name', 'category', 'entry_day', 'scanned_at', 'scanned_by')
    list_filter = ('entry_day', 'category')
    search_fields = ('ticket_code', 'name', 'email')
    ordering = ('-scanned_at',)
    readonly_fields = ('scanned_at',)
