import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from statistics import mean

from django.db import transaction
from django.db.models import Avg, Count
from django.utils import timezone

from apps.ai.models import AIAgentRun
from apps.common.timezones import business_localdate
from apps.daily.models import DailyMetricRecord, DailyMetricSummary, DailyRecordDetailLevel, DailySummaryWindow
from apps.users.models import DynamicProfile, StableProfile
from apps.wallet.models import CurrencyType, TransactionReason
from apps.wallet.services import change_balance

DAILY_REWARD_MIN = 0
DAILY_REWARD_MAX = 40


def round_5(value: float) -> int:
    return int(round(value / 5) * 5)


def clamp(value: int, lower: int, upper: int) -> int:
    return min(max(value, lower), upper)


def parse_hhmm(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (TypeError, ValueError) as exc:
        raise ValueError("time fields must use HH:MM format") from exc


def minutes_of_day(value: time) -> int:
    return value.hour * 60 + value.minute


def circular_sleep_hours(*, sleep_time: time, wake_time: time) -> float:
    sleep_min = minutes_of_day(sleep_time)
    wake_min = minutes_of_day(wake_time)
    duration = (wake_min - sleep_min) % (24 * 60)
    if duration == 0:
        duration = 24 * 60
    return round(duration / 60, 2)


def score_range(value: float, ideal_min: float, ideal_max: float, ok_min: float, ok_max: float) -> int:
    if ideal_min <= value <= ideal_max:
        return 100
    if ok_min <= value <= ok_max:
        return 70
    if value < ok_min:
        distance = ok_min - value
    else:
        distance = value - ok_max
    return max(0, int(55 - distance * 18))


def profile_targets(user) -> dict:
    stable = getattr(user, "stable_profile", None)
    dynamic = getattr(user, "dynamic_profile", None)
    chronotype = getattr(stable, "chronotype", "undisclosed") if stable else "undisclosed"
    stress_level = getattr(dynamic, "stress_level", None) if dynamic else None
    sleep_quality = getattr(dynamic, "sleep_quality", "undisclosed") if dynamic else "undisclosed"

    if chronotype == StableProfile.Chronotype.NIGHT:
        wake_ideal = (8 * 60, 10 * 60 + 30)
        wake_ok = (7 * 60, 11 * 60 + 30)
        sleep_ideal = (0, 2 * 60)
        sleep_ok = (23 * 60, 3 * 60)
    elif chronotype == StableProfile.Chronotype.MORNING:
        wake_ideal = (6 * 60, 8 * 60)
        wake_ok = (5 * 60 + 30, 9 * 60)
        sleep_ideal = (21 * 60 + 30, 23 * 60)
        sleep_ok = (21 * 60, 24 * 60 - 1)
    else:
        wake_ideal = (6 * 60 + 30, 9 * 60)
        wake_ok = (6 * 60, 10 * 60)
        sleep_ideal = (22 * 60, 24 * 60 - 1)
        sleep_ok = (21 * 60 + 30, 1 * 60)

    phone_ideal = 150 if stress_level and stress_level >= 8 else 120
    phone_ok = 270 if stress_level and stress_level >= 8 else 240
    if sleep_quality == DynamicProfile.ThreeLevelState.LOW:
        phone_ok += 30

    return {
        "chronotype": chronotype,
        "stress_level": stress_level,
        "sleep_quality": sleep_quality,
        "wake_ideal": wake_ideal,
        "wake_ok": wake_ok,
        "sleep_ideal": sleep_ideal,
        "sleep_ok": sleep_ok,
        "phone_ideal": phone_ideal,
        "phone_ok": phone_ok,
    }


def time_score(value_minutes: int, ideal: tuple[int, int], ok: tuple[int, int]) -> int:
    # Handles windows that may cross midnight.
    def in_window(value, window):
        start, end = window
        if start <= end:
            return start <= value <= end
        return value >= start or value <= end

    if in_window(value_minutes, ideal):
        return 100
    if in_window(value_minutes, ok):
        return 70
    return 35


def evaluate_metrics(*, user, wake_time: time, sleep_time: time, phone_minutes: int, water_cups: int, history: dict) -> dict:
    targets = profile_targets(user)
    sleep_hours = circular_sleep_hours(sleep_time=sleep_time, wake_time=wake_time)
    wake_score = time_score(minutes_of_day(wake_time), targets["wake_ideal"], targets["wake_ok"])
    sleep_start_score = time_score(minutes_of_day(sleep_time), targets["sleep_ideal"], targets["sleep_ok"])
    sleep_duration_score = score_range(sleep_hours, 7, 9, 6, 10)
    sleep_score = int((sleep_start_score * 0.45) + (sleep_duration_score * 0.55))

    if phone_minutes <= targets["phone_ideal"]:
        phone_score = 100
    elif phone_minutes <= targets["phone_ok"]:
        phone_score = 70
    elif phone_minutes <= targets["phone_ok"] + 120:
        phone_score = 40
    else:
        phone_score = 15

    if water_cups >= 6:
        water_score = 100
    elif water_cups >= 4:
        water_score = 75
    elif water_cups >= 2:
        water_score = 45
    else:
        water_score = 10

    total_score = int(wake_score * 0.2 + sleep_score * 0.35 + phone_score * 0.25 + water_score * 0.2)
    reward = clamp(round_5(total_score / 100 * DAILY_REWARD_MAX), DAILY_REWARD_MIN, DAILY_REWARD_MAX)

    if history.get("recent_7d", {}).get("count", 0) >= 3 and total_score >= history["recent_7d"].get("avg_score", 0) + 8:
        reward = clamp(reward + 5, DAILY_REWARD_MIN, DAILY_REWARD_MAX)

    feedback_parts = []
    if sleep_score >= 80:
        feedback_parts.append("??????")
    else:
        feedback_parts.append("???????????????")
    if phone_score < 60:
        feedback_parts.append("?????????????? 30 ??")
    if water_score >= 75:
        feedback_parts.append("???????")
    else:
        feedback_parts.append("??????????? 4 ?")
    if targets["stress_level"] and targets["stress_level"] >= 8:
        feedback_parts.append("?????????????????")

    return {
        "score": total_score,
        "reward_primary": reward,
        "feedback": "?".join(feedback_parts) + "?",
        "metric_scores": {
            "wake_time": wake_score,
            "sleep": sleep_score,
            "phone_minutes": phone_score,
            "water_cups": water_score,
        },
        "sleep_hours": sleep_hours,
        "targets": targets,
        "reward_range": {"min": DAILY_REWARD_MIN, "max": DAILY_REWARD_MAX},
    }


def recent_history(user, target_date: date) -> dict:
    windows = {
        "recent_7d": target_date - timedelta(days=7),
        "recent_30d": target_date - timedelta(days=30),
        "recent_1y": target_date - timedelta(days=365),
    }
    result = {}
    for key, start in windows.items():
        qs = DailyMetricRecord.objects.filter(owner=user, record_date__gte=start, record_date__lt=target_date)
        aggregate = qs.aggregate(count=Count("id"), avg_score=Avg("score"), avg_reward=Avg("reward_primary"))
        result[key] = {
            "count": aggregate["count"] or 0,
            "avg_score": round(float(aggregate["avg_score"] or 0), 1),
            "avg_reward": round(float(aggregate["avg_reward"] or 0), 1),
        }
    summaries = DailyMetricSummary.objects.filter(owner=user, bucket_end__lt=target_date).order_by("-bucket_end")[:6]
    result["summaries"] = [summary.summary_payload for summary in summaries]
    return result


def summarize_records(records, *, label: str) -> tuple[str, dict]:
    if not records:
        return "No records.", {"label": label, "count": 0}
    avg_score = round(mean(record.score for record in records), 1)
    avg_reward = round(mean(record.reward_primary for record in records), 1)
    avg_phone = round(mean(record.phone_minutes for record in records), 1)
    avg_water = round(mean(record.water_cups for record in records), 1)
    text = f"{label}: {len(records)} records, avg score {avg_score}, avg reward {avg_reward}, avg phone {avg_phone} min, avg water {avg_water} cups."
    return text, {
        "label": label,
        "count": len(records),
        "avg_score": avg_score,
        "avg_reward": avg_reward,
        "avg_phone_minutes": avg_phone,
        "avg_water_cups": avg_water,
    }


def compress_daily_history(*, user, today: date) -> None:
    cutoff_7 = today - timedelta(days=7)
    cutoff_30 = today - timedelta(days=30)
    cutoff_365 = today - timedelta(days=365)

    DailyMetricRecord.objects.filter(owner=user, record_date__lt=cutoff_365).delete()
    DailyMetricSummary.objects.filter(owner=user, bucket_end__lt=cutoff_365).delete()

    recent_records = list(
        DailyMetricRecord.objects.filter(owner=user, record_date__gte=cutoff_30, record_date__lt=cutoff_7)
    )
    if recent_records:
        text, payload = summarize_records(recent_records, label="7d-30d")
        DailyMetricSummary.objects.update_or_create(
            owner=user,
            window_type=DailySummaryWindow.RECENT_7D_30D,
            bucket_start=cutoff_30,
            bucket_end=cutoff_7 - timedelta(days=1),
            defaults={"record_count": len(recent_records), "summary_text": text, "summary_payload": payload},
        )
        DailyMetricRecord.objects.filter(id__in=[record.id for record in recent_records]).update(
            detail_level=DailyRecordDetailLevel.REDUCED,
            agent_feedback="",
            profile_snapshot={},
            history_snapshot={},
            agent_payload={},
        )

    old_records = list(
        DailyMetricRecord.objects.filter(owner=user, record_date__gte=cutoff_365, record_date__lt=cutoff_30)
    )
    buckets: dict[tuple[date, date], list[DailyMetricRecord]] = {}
    for record in old_records:
        start = record.record_date.replace(day=1)
        end = record.record_date.replace(day=calendar.monthrange(record.record_date.year, record.record_date.month)[1])
        buckets.setdefault((start, min(end, cutoff_30 - timedelta(days=1))), []).append(record)
    for (start, end), records in buckets.items():
        text, payload = summarize_records(records, label=f"{start.isoformat()} monthly")
        DailyMetricSummary.objects.update_or_create(
            owner=user,
            window_type=DailySummaryWindow.MONTHLY_30D_1Y,
            bucket_start=start,
            bucket_end=end,
            defaults={"record_count": len(records), "summary_text": text, "summary_payload": payload},
        )
    if old_records:
        DailyMetricRecord.objects.filter(id__in=[record.id for record in old_records]).delete()


@transaction.atomic
def evaluate_daily_metrics(*, user, record_date=None, wake_time, sleep_time, phone_minutes, water_cups):
    record_date = record_date or business_localdate()
    if phone_minutes < 0 or water_cups < 0:
        raise ValueError("daily metric values must not be negative")

    wake = parse_hhmm(wake_time) if isinstance(wake_time, str) else wake_time
    sleep = parse_hhmm(sleep_time) if isinstance(sleep_time, str) else sleep_time
    existing = DailyMetricRecord.objects.select_for_update().filter(owner=user, record_date=record_date).first()
    if existing:
        return existing, False

    StableProfile.objects.get_or_create(user=user)
    DynamicProfile.objects.get_or_create(user=user)
    history = recent_history(user, record_date)
    profile_snapshot = user.build_prompt_profile()
    result = evaluate_metrics(
        user=user,
        wake_time=wake,
        sleep_time=sleep,
        phone_minutes=phone_minutes,
        water_cups=water_cups,
        history=history,
    )

    record = DailyMetricRecord.objects.create(
        owner=user,
        record_date=record_date,
        wake_time=wake,
        sleep_time=sleep,
        phone_minutes=phone_minutes,
        water_cups=water_cups,
        score=result["score"],
        reward_primary=result["reward_primary"],
        agent_feedback=result["feedback"],
        profile_snapshot=profile_snapshot,
        history_snapshot=history,
        agent_payload=result,
    )

    if record.reward_primary:
        _, tx = change_balance(
            user=user,
            currency_type=CurrencyType.PRIMARY,
            delta=record.reward_primary,
            reason=TransactionReason.TASK_REWARD,
            reference_type="daily_metric_record",
            reference_id=record.id,
            memo="Daily metric reward",
            payload={"score": record.score, "reward_range": result["reward_range"]},
        )
        record.reward_transaction = tx
        record.save(update_fields=["reward_transaction", "updated_at"])

    AIAgentRun.objects.create(
        owner=user,
        workflow_key="daily_metric_evaluation",
        status=AIAgentRun.Status.SUCCEEDED,
        input_payload={
            "record_date": record_date.isoformat(),
            "wake_time": wake_time,
            "sleep_time": sleep_time,
            "phone_minutes": phone_minutes,
            "water_cups": water_cups,
        },
        context_payload={"profile": profile_snapshot, "history": history},
        result_payload=result,
        finished_at=timezone.now(),
    )
    compress_daily_history(user=user, today=record_date)
    return record, True
