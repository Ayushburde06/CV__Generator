from django.db import models

# Create your models here.
class Profile(models.Model):
    name = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    phone = models.CharField(max_length=200)
    github_url = models.CharField(max_length=500, default="")
    linkedin_url = models.CharField(max_length=500, default="")
    summary = models.TextField(max_length=2000)
    degree = models.CharField(max_length=200)
    university = models.CharField(max_length=200)
    projects = models.TextField(max_length=1000, default="")
    skills = models.TextField(max_length=1000)
    certifications = models.TextField(max_length=2000, default="")