from django.db import transaction


@transaction.atomic
def grant_experience(*, user, amount):
    if amount <= 0:
        raise ValueError("经验值必须为正数")

    user = user.__class__.objects.select_for_update().get(pk=user.pk)
    before = {
        "level": user.level,
        "experience": user.experience,
        "total_experience": user.total_experience,
    }

    user.experience += amount
    user.total_experience += amount
    leveled_up = False

    while user.experience >= user.next_level_experience:
        user.experience -= user.next_level_experience
        user.level += 1
        leveled_up = True

    user.save(update_fields=["level", "experience", "total_experience", "updated_at"])
    return {
        "before": before,
        "after": {
            "level": user.level,
            "experience": user.experience,
            "total_experience": user.total_experience,
            "next_level_experience": user.next_level_experience,
        },
        "gained_experience": amount,
        "leveled_up": leveled_up,
    }
