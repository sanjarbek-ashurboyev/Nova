from django.db import migrations


def backfill_role(apps, schema_editor):
    # 0001_initial 'role' ustunini default'siz qo'shgan, shuning uchun
    # eski qatorlarda role='' bo'lib qolgan. Ularni 'user' ga to'ldiramiz.
    User = apps.get_model('accounts', 'User')
    User.objects.exclude(role__in=['user', 'operator']).update(role='user')


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0007_alter_user_district_alter_user_referrer_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_role, migrations.RunPython.noop),
    ]
