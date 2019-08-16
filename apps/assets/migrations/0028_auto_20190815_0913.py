# Generated by Django 2.1.7 on 2019-08-15 01:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0027_project'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='environment',
            field=models.CharField(choices=[('DEV', 'dev'), ('TEST', 'test'), ('DEMO', 'demo'), ('TDEMO', 'tdemo'), ('PROD', 'prod'), ('Other', 'other')], default='DEV', max_length=32, verbose_name='Environment'),
        ),
        migrations.AddField(
            model_name='asset',
            name='projects',
            field=models.ManyToManyField(blank=True, related_name='assets', to='assets.Project', verbose_name='Projects'),
        ),
    ]