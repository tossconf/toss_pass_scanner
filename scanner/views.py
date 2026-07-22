import json
import sqlite3
from datetime import date, datetime

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import IntegrityError

from .models import EntryLog


# ─── Helpers ─────────────────────────────────────────────────────────────────

TICKETS_DB_PATH = settings.TICKETS_DB_PATH

EVENT_DAYS = ['2026-07-23', '2026-07-24', '2026-07-25']


def lookup_ticket(ticket_code: str) -> dict | None:
    """Check tickets.db for the given ticket_code. Returns row dict or None."""
    try:
        conn = sqlite3.connect(str(TICKETS_DB_PATH))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT ticket_code, name, email, category FROM tickets WHERE ticket_code = ?",
            (ticket_code,)
        )
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def get_today_event_day() -> str | None:
    """Return today's date as string if it's an event day, else None."""
    today = date.today().isoformat()
    return today if today in EVENT_DAYS else None


# ─── Views ───────────────────────────────────────────────────────────────────

def scan_view(request):
    """Main QR scanner page."""
    event_day = get_today_event_day()
    # Allow manual day override via query param for testing
    override_day = request.GET.get('day')
    if override_day and override_day in EVENT_DAYS:
        event_day = override_day

    context = {
        'event_day': event_day,
        'event_days': EVENT_DAYS,
        'is_event_day': event_day is not None,
    }
    return render(request, 'scanner/scan.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def process_qr(request):
    """
    API endpoint to process a decoded QR code payload.

    Expected POST body (JSON):
        {
            "qr_data": "{\"category\":\"General\",\"name\":\"...\",\"email\":\"...\",\"id\":\"T26-G-001\"}",
            "entry_day": "2026-07-23",
            "scanned_by": "Volunteer Name"   (optional)
        }
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, Exception) as ex:
        return JsonResponse({'status': 'error ' + str(ex), 'message': 'Invalid request body.'}, status=400)

    qr_raw = body.get('qr_data', '')
    entry_day = body.get('entry_day', '')
    scanned_by = body.get('scanned_by', '').strip()

    # --- Validate day ---
    if entry_day not in EVENT_DAYS:
        return JsonResponse({
            'status': 'error',
            'message': f'"{entry_day}" is not a valid event day.'
        }, status=400)

    # --- Decode QR payload ---
    try:
        qr_payload = json.loads(qr_raw)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({
            'status': 'invalid',
            'message': 'QR code could not be decoded. Not a TOSSConf pass.'
        }, status=400)

    ticket_code = qr_payload.get('id', '').strip()
    if not ticket_code:
        return JsonResponse({
            'status': 'invalid',
            'message': 'QR code does not contain a valid ticket ID.'
        }, status=400)

    # --- Validate against tickets.db ---
    ticket = lookup_ticket(ticket_code)
    if not ticket:
        return JsonResponse({
            'status': 'invalid',
            'message': f'Ticket "{ticket_code}" not found in the system. Pass may be fake.'
        }, status=404)

    # --- Check for duplicate entry ---
    already_entered = EntryLog.objects.filter(
        ticket_code=ticket_code,
        entry_day=entry_day
    ).first()

    if already_entered:
        scanned_time = already_entered.scanned_at.strftime('%I:%M %p')
        return JsonResponse({
            'status': 'duplicate',
            'message': f'{ticket["name"]} already checked in today at {scanned_time}.',
            'attendee': {
                'name': ticket['name'],
                'email': ticket['email'],
                'category': ticket['category'],
                'ticket_code': ticket_code,
                'scanned_at': scanned_time,
            }
        })

    # --- Record the entry ---
    try:
        entry = EntryLog.objects.create(
            ticket_code=ticket_code,
            name=ticket['name'],
            email=ticket['email'],
            category=ticket['category'],
            entry_day=entry_day,
            scanned_by=scanned_by,
        )
        return JsonResponse({
            'status': 'success',
            'message': f'Welcome, {ticket["name"]}! Entry recorded for {entry_day}.',
            'attendee': {
                'name': ticket['name'],
                'email': ticket['email'],
                'category': ticket['category'],
                'ticket_code': ticket_code,
                'entry_day': entry_day,
                'scanned_at': entry.scanned_at.strftime('%I:%M %p'),
            }
        })
    except IntegrityError:
        # Race condition: duplicate scan hit simultaneously
        return JsonResponse({
            'status': 'duplicate',
            'message': f'{ticket["name"]} was just checked in. Duplicate scan.'
        })


def dashboard_view(request):
    """Admin dashboard showing entry stats."""
    # Per-day counts
    day_stats = []
    day_labels = {
        '2026-07-23': 'Day 1 — July 23',
        '2026-07-24': 'Day 2 — July 24',
        '2026-07-25': 'Day 3 — July 25',
    }
    for day in EVENT_DAYS:
        entries = EntryLog.objects.filter(entry_day=day)
        cats = {}
        for e in entries:
            cats[e.category] = cats.get(e.category, 0) + 1
        day_stats.append({
            'day': day,
            'label': day_labels[day],
            'total': entries.count(),
            'categories': cats,
        })

    # Total unique attendees across all days
    total_unique = EntryLog.objects.values('ticket_code').distinct().count()

    # Recent entries (last 20)
    recent = EntryLog.objects.select_related().order_by('-scanned_at')[:20]

    # Category totals (across all days)
    all_entries = EntryLog.objects.all()
    cat_totals = {}
    for e in all_entries:
        cat_totals[e.category] = cat_totals.get(e.category, 0) + 1

    context = {
        'day_stats': day_stats,
        'total_unique': total_unique,
        'recent': recent,
        'cat_totals': cat_totals,
        'event_days': EVENT_DAYS,
    }
    return render(request, 'scanner/dashboard.html', context)
