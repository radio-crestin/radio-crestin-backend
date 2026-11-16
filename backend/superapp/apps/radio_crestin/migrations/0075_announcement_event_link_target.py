from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0074_announcement_icon_any_file'),
    ]

    operations = [
        migrations.AlterField(
            model_name='announcementevent',
            name='target',
            field=models.CharField(blank=True, choices=[('card', 'Card'), ('button', 'Button'), ('link', 'Link in the description')], default='', help_text='For clicks: the whole card, the button or a link in the description.', max_length=16, verbose_name='Tapped'),
        ),
    ]
