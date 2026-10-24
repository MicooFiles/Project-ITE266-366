# W.I.L.D. CARE: Post-Flood Disease Monitoring System
# MIT LISENCE
# Copyright (c) 2026 Jairus Corro. All rights reserved.
# Licensed under the W.I.L.D. CARE Educational License (see LICENSE.txt). Provided "AS IS", without warranty.
# Not a medical device. Do not use it for real clinical or emergency decisions.

"""Resident notifications.

Turns a health worker's assessment into three messages: an SMS (kept to one 160-character segment whenever possible),
an email, and an in-app alert. Pure Python (no tkinter, no database), so it can be tested on its own.
"""

import html
import math
import re

PRIORITY = "Priority Hospital Visit Needed"
CHECKUP = "Check-up Recommended"
STATUS_CHOICES = [PRIORITY, CHECKUP]

EMERGENCY_NUMBER = "911"
SIGN_OFF = "W.I.L.D. CARE Health Team"

# Shortened one by one, and only when the SMS would not otherwise fit in a single segment.
_ABBREVIATIONS = (("Barangay", "Brgy."), ("Hospital", "Hosp."), ("Rural Health Unit", "RHU"),
                  ("Medical Center", "Med Ctr"), ("District", "Dist."))

# GSM 03.38 7-bit alphabet. Any other character switches the whole SMS to Unicode (70 characters per segment).
_GSM_BASIC = ("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡"
              "ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà")
_GSM_EXTENDED = "^{}\\[~]|€"      # each of these takes two units
_TYPOGRAPHY = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-",
               "\u2026": "...", "\u00a0": " ", "\u2022": "-"}


def clean(text, limit=None):
    """One line of plain text: control characters and line breaks become single spaces."""
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", str(text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].rstrip() if limit else text


def normalize_mobile(text):
    """A Philippine mobile number as 09XXXXXXXXX, or '' when it is not one. Accepts 0917 123 4567, +63 917..., 639171234567, 9171234567."""
    digits = re.sub(r"\D", "", str(text or ""))
    if digits.startswith("63") and len(digits) == 12:
        digits = "0" + digits[2:]
    elif len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits
    return digits if re.fullmatch(r"09\d{9}", digits) else ""


def mask_mobile(number):
    """09171234567 -> 0917•••4567 (what the log keeps instead of the full number)."""
    return f"{number[:4]}\u2022\u2022\u2022{number[-4:]}" if len(number) == 11 else ""


def _sentence(text):
    return text if not text or text[-1] in ".!?" else text + "."


# ── SMS ──────────────────────────────────────────────────────────────────────
def sms_info(text):
    """Length facts for an SMS: {'text', 'units', 'segments', 'encoding', 'limit'}."""
    text = "".join(_TYPOGRAPHY.get(c, c) for c in text)
    if all(c in _GSM_BASIC or c in _GSM_EXTENDED for c in text):
        units, single, multi, encoding = sum(2 if c in _GSM_EXTENDED else 1 for c in text), 160, 153, "GSM-7"
    else:
        units, single, multi, encoding = len(text.encode("utf-16-le")) // 2, 70, 67, "Unicode"
    segments = 1 if units <= single else math.ceil(units / multi)
    return {"text": text, "units": units, "segments": segments, "encoding": encoding, "limit": single}


def _one_segment(text):
    return sms_info(text)["segments"] == 1


def _assemble(head, parts, tail, drop):
    """Join the message. parts = [(rank, text)] in display order; with drop=True the highest rank
    (least important) goes first until the message fits one segment."""
    kept = list(range(len(parts)))
    while True:
        text = " ".join([head] + [parts[i][1] for i in kept] + [tail])
        if not drop or _one_segment(text) or not kept:
            return text
        kept.remove(max(kept, key=lambda i: parts[i][0]))


def build_sms(name, status, facility, instructions, hotline):
    """Short and direct. Never names the illness: an SMS can be read by anyone holding the phone."""
    urgent = status == PRIORITY
    extra = _sentence(instructions)

    def make(place, drop):
        if urgent:
            head = f"WILD CARE URGENT: {name}, go to {place} triage NOW (priority)."
            parts = [(3, extra) if extra else None, (1, "Bring ID/PhilHealth."), (2, f"Help: {hotline}.")]
            tail = f"Emergency: {EMERGENCY_NUMBER}"
        else:
            head = f"WILD CARE: {name}, please visit {place} for a check-up."
            parts = [(3, extra or "Please go as soon as you can."), (1, "Bring ID."), (2, f"Info: {hotline}.")]
            tail = f"Emergency? Call {EMERGENCY_NUMBER}"
        return _assemble(head, [p for p in parts if p], tail, drop)

    places = [facility]
    for long, short in _ABBREVIATIONS:
        places.append(re.sub(long, short, places[-1], flags=re.I))
    for place in places:
        if _one_segment(make(place, drop=False)):
            return sms_info(make(place, drop=False))
    full = make(places[-1], drop=False)
    # Unicode allows only 70 characters per segment, so stripping the message to fit would remove the instructions:
    # keep it whole and let the caller show the segment count.
    return sms_info(full if sms_info(full)["encoding"] != "GSM-7" else make(places[-1], drop=True))


# ── Email / in-app message ───────────────────────────────────────────────────
def _email_parts(name, status, facility, symptoms, instructions, hotline):
    urgent = status == PRIORITY
    logged = f"your logged symptoms ({symptoms})" if symptoms else "your report"
    from_worker = [f"From your health worker: {_sentence(instructions)}"] if instructions else []
    if urgent:
        return {
            "subject": f"URGENT: Please go to {facility} now for priority triage",
            "intro": (f"Your health worker at W.I.L.D. CARE reviewed {logged} and recommends that you be seen by a doctor "
                      "right away. Some illnesses that follow floods can get worse quickly if care is delayed. "
                      "This message is not a diagnosis; a doctor needs to examine you."),
            "sections": [
                ("What to do now", from_worker + [
                    f"Go to {facility} now. Please do not wait to see if you feel better.",
                    "Go straight to the triage desk and tell the staff you were referred by your health worker for priority triage.",
                    "Ask a family member or neighbor to go with you, and avoid walking through floodwater on the way.",
                    "Do not start new medicines on your own before the doctor sees you. Tell the staff what you have already taken."]),
                ("What to bring", [
                    "Valid ID and PhilHealth card or MDR (if you have one)",
                    "A note of when your symptoms started, and when and where you were in floodwater",
                    "The medicines you are taking, and any allergies",
                    "This message, as proof of your referral"]),
                ("Emergency contacts", (
                    f"If you have trouble breathing, chest pain, confusion, bleeding, seizures, or cannot keep fluids down, "
                    f"call {EMERGENCY_NUMBER} or your local CDRRMC/RHU emergency hotline right away. "
                    f"Questions about this referral: {hotline}.")),
            ],
            "closing": "We are thinking of you and hope you feel better soon.",
        }
    return {
        "subject": f"Check-up recommended: please visit {facility}",
        "intro": (f"Thank you for reporting to W.I.L.D. CARE. After reviewing {logged}, your health worker recommends a "
                  f"check-up at {facility}. This is not an emergency right now, but an early visit helps catch problems "
                  "sooner, and the health worker can check whether preventive treatment (prophylaxis) is right for you."),
        "sections": [
            ("What to do", from_worker + [
                f"Visit {facility} during clinic hours" + ("" if instructions else ", as soon as you can") +
                ", and tell the front desk that W.I.L.D. CARE advised you to come in.",
                "Drink only boiled or bottled water, and take oral rehydration solution if you have diarrhea.",
                "Wash your hands with soap before eating and after using the toilet.",
                "Stay out of floodwater. If you cannot, wear boots and wash your skin with soap and clean water afterward.",
                "Go to a hospital sooner if you get a high fever, bloody stools, repeated vomiting, or cannot keep fluids down."]),
            ("What to bring", [
                "Valid ID and PhilHealth card (if you have one)",
                "A short list of your symptoms and when they started",
                "Your current medicines and any allergies"]),
            ("Emergency contacts", (
                f"For a life-threatening emergency, call {EMERGENCY_NUMBER} or your local CDRRMC/RHU emergency hotline. "
                f"Questions about your check-up: {hotline}.")),
        ],
        "closing": "Take care, and we hope to see you soon.",
    }


def _plain(name, parts):
    lines = [f"Dear {name},", "", parts["intro"], ""]
    for heading, body in parts["sections"]:
        lines.append(heading)
        lines += [f"- {item}" for item in body] if isinstance(body, list) else [body]
        lines.append("")
    lines += [parts["closing"], SIGN_OFF]
    return "\n".join(lines)


def _html(name, urgent, parts):
    e, color = html.escape, ("#B42318" if urgent else "#0F766E")
    blocks = []
    for heading, body in parts["sections"]:
        content = ("<ul style=\"margin:0 0 6px 18px;padding:0;\">" + "".join(f"<li style=\"margin:4px 0;\">{e(i)}</li>" for i in body) + "</ul>"
                   if isinstance(body, list) else f"<p style=\"margin:6px 0;\">{e(body)}</p>")
        blocks.append(f"<h3 style=\"color:{color};margin:18px 0 4px;font-size:15px;\">{e(heading)}</h3>{content}")
    return (
        "<html><body style=\"margin:0;padding:20px;background:#F3F5F9;font-family:Segoe UI,Arial,sans-serif;color:#14203A;\">"
        "<div style=\"max-width:560px;margin:0 auto;background:#FFFFFF;border-radius:12px;border:1px solid #D8DEE8;overflow:hidden;\">"
        f"<div style=\"background:{color};color:#FFFFFF;padding:14px 24px;font-weight:bold;letter-spacing:1px;\">"
        f"{'URGENT HEALTH NOTICE' if urgent else 'HEALTH NOTICE'} &#8212; W.I.L.D. CARE</div>"
        f"<div style=\"padding:8px 24px 24px;line-height:1.5;font-size:14px;\"><p>Dear {e(name)},</p><p>{e(parts['intro'])}</p>"
        f"{''.join(blocks)}<p style=\"margin-top:20px;\">{e(parts['closing'])}<br><strong>{e(SIGN_OFF)}</strong></p></div>"
        "<div style=\"padding:12px 24px;background:#F3F5F9;color:#5A6781;font-size:12px;\">Sent by W.I.L.D. CARE for your local "
        "health worker. This is a student-project system and not a medical device.</div></div></body></html>")


def build_push(status, facility):
    if status == PRIORITY:
        return "Urgent: go to the hospital now", f"Your health worker referred you to {facility} for priority triage. Open for steps."
    return "Check-up recommended", f"Please visit {facility} for a check-up. Open to see what to bring."


def validate(patient_name, status, facility, hotline):
    """Returns an error message, or '' when the notification can be sent."""
    if not clean(patient_name):
        return "This record has no patient name."
    if status not in STATUS_CHOICES:
        return "Choose an assessment."
    if not clean(facility):
        return "Enter the facility or station the resident should go to."
    if not clean(hotline):
        return "Enter a contact number or hotline."
    return ""


def build_notification(patient_name, status, facility, symptoms="", instructions="", hotline=""):
    """All three messages for one resident. Inputs follow the W.I.L.D. CARE fields:
    patient name, health worker status, facility, symptoms logged, instructions and hotline."""
    name, place, hotline = clean(patient_name, 80), clean(facility, 80), clean(hotline, 60)
    symptoms, instructions = clean(symptoms, 200), clean(instructions, 240)
    urgent = status == PRIORITY
    parts = _email_parts(name, status, place, symptoms, instructions, hotline)
    push_title, push_body = build_push(status, place)
    sms = build_sms(name, status, place, instructions, hotline)
    return {"status": status, "urgent": urgent, "tone": "danger" if urgent else "ok",
            "sms": sms["text"], "sms_info": sms, "push_title": push_title, "push_body": push_body,
            "email_subject": parts["subject"], "email_body": _plain(name, parts), "email_html": _html(name, urgent, parts)}
