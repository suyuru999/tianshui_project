from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('environment', '0021_climatedatafile_zip_only'),
    ]

    operations = [
        migrations.AlterField(
            model_name='climatedatafile',
            name='file_type',
            field=models.CharField(
                choices=[
                    ('csv', 'CSV'),
                    ('xlsx', 'Excel'),
                    ('xls', 'Excel 97-2003'),
                    ('tif', 'GeoTIFF'),
                    ('tiff', 'GeoTIFF'),
                    ('zip', 'ZIP'),
                ],
                default='zip',
                max_length=10,
                verbose_name='文件类型',
            ),
        ),
    ]
