from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduled_reminders = []

def parse_timing_to_hours(timing: str) -> list:
    timing_lower = timing.lower()
    if "once" in timing_lower or "od" in timing_lower:
        return [8]
    elif "twice" in timing_lower or "bd" in timing_lower or "bid" in timing_lower:
        return [8, 20]
    elif "three" in timing_lower or "tds" in timing_lower or "tid" in timing_lower:
        return [8, 14, 20]
    elif "four" in timing_lower or "qid" in timing_lower:
        return [8, 12, 16, 20]
    elif "morning" in timing_lower and "night" in timing_lower:
        return [8, 21]
    elif "morning" in timing_lower:
        return [8]
    elif "night" in timing_lower or "bedtime" in timing_lower:
        return [21]
    elif "afternoon" in timing_lower:
        return [14]
    return [8]

def schedule_reminders(medications: list, phone: str, whatsapp: str):
    from twilio_service import send_medication_reminder
    global scheduled_reminders

    for med in medications:
        hours = parse_timing_to_hours(med.get("timing", "once daily"))
        for hour in hours:
            job_id = f"{med['name']}_{hour}"
            def make_job(m, p, w):
                def job():
                    send_medication_reminder(p, w, m["name"], m["dosage"], m["timing"])
                return job
            scheduler.add_job(
                make_job(med, phone, whatsapp),
                'cron',
                hour=hour,
                minute=0,
                id=job_id,
                replace_existing=True
            )
            scheduled_reminders.append({
                "medicine": med["name"],
                "dosage": med["dosage"],
                "hour": f"{hour:02d}:00",
                "phone": phone,
                "whatsapp": whatsapp
            })
    return scheduled_reminders

def start_scheduler():
    if not scheduler.running:
        scheduler.start()

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()

def get_scheduled_reminders():
    return scheduled_reminders