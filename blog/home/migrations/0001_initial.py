# Generated by Django 2.2 on 2022-01-19 11:24

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ArticleCtegory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=100)),
                ('created', models.DateField(default=django.utils.timezone.now)),
            ],
            options={
                'verbose_name': '类别管理',
                'verbose_name_plural': '类别管理',
                'db_table': 'tb_category',
            },
        ),
    ]