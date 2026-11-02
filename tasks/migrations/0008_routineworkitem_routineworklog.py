# Generated for RoutineWorkItem and RoutineWorkLog models

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0007_userdevice_usersessionlog'),
    ]

    operations = [
        migrations.CreateModel(
            name='RoutineWorkItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('frequency', models.CharField(choices=[('DAILY', 'Daily'), ('WEEKLY', 'Weekly'), ('MONTHLY', 'Monthly'), ('YEARLY', 'Yearly')], db_index=True, default='DAILY', max_length=20)),
                ('priority', models.CharField(choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('URGENT', 'Urgent')], default='MEDIUM', max_length=20)),
                ('target_time', models.CharField(blank=True, default='', max_length=100)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('last_completed_at', models.DateTimeField(blank=True, null=True)),
                ('completion_notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_routine_items', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_routine_items', to=settings.AUTH_USER_MODEL)),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='routine_items', to='tasks.department')),
                ('last_completed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='completed_routine_items', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['frequency', 'created_at'],
            },
        ),
        migrations.CreateModel(
            name='RoutineWorkLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('completed_at', models.DateTimeField(auto_now_add=True)),
                ('period_identifier', models.CharField(db_index=True, max_length=50)),
                ('notes', models.TextField(blank=True, default='')),
                ('status', models.CharField(default='COMPLETED', max_length=20)),
                ('completed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='routine_logs', to=settings.AUTH_USER_MODEL)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='tasks.routineworkitem')),
            ],
            options={
                'ordering': ['-completed_at'],
                'unique_together': {('item', 'period_identifier')},
            },
        ),
    ]

