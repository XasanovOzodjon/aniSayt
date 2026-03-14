from django.db import models
from anime.models import Anime


class Person(models.Model):
    fullname = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    age = models.CharField(max_length=3)
    photo = models.ImageField(upload_to='person_photos/')
    anime = models.ForeignKey(Anime, related_name='persons', on_delete=models.CASCADE)
    rating = models.FloatField(default=0.0)
    
    
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    

    def __str__(self):
        return self.fullname