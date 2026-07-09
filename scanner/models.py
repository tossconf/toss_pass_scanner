from django.db import models


class EntryLog(models.Model):
    """Records each entry scan for TOSSConf 2026."""

    DAY_CHOICES = [
        ('2026-07-23', 'Day 1 — July 23, 2026'),
        ('2026-07-24', 'Day 2 — July 24, 2026'),
        ('2026-07-25', 'Day 3 — July 25, 2026'),
    ]

    ticket_code = models.CharField(max_length=30, help_text="e.g. T26-G-001")
    name = models.CharField(max_length=200)
    email = models.EmailField()
    category = models.CharField(max_length=50)
    entry_day = models.DateField(choices=DAY_CHOICES)
    scanned_at = models.DateTimeField(auto_now_add=True)
    scanned_by = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        unique_together = ('ticket_code', 'entry_day')
        ordering = ['-scanned_at']
        verbose_name = 'Entry Log'
        verbose_name_plural = 'Entry Logs'

    def __str__(self):
        return f"{self.ticket_code} | {self.name} | {self.entry_day}"
