from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('environment', '0020_climateanalysisresult_processing_task'),
    ]

    operations = [
        migrations.AlterField(
            model_name='climatedatafile',
            name='file_type',
            field=models.CharField(
                choices=[('zip', 'ZIP')],
                default='zip',
                max_length=10,
                verbose_name='文件类型',
            ),
        ),
    ]
