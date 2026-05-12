from django.db import models

# Create your models here.
from django.db import models

class UploadedLAS(models.Model):
    file = models.FileField(upload_to='las/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name

# Create your models here.
class Well(models.Model):
    name = models.CharField(max_length=100)

    depth_data = models.JSONField()
    density_log = models.JSONField()
    resistivity_log = models.JSONField()

    def __str__(self):
        return self.name