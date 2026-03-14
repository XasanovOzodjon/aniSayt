from django.db import models

class Ganre(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name
    
class Anime(models.Model):
    title = models.CharField(max_length=255)
    discription = models.TextField()
    poster = models.ImageField(upload_to="anime/posters/")
    release_year = models.IntegerField()
    ganres = models.ManyToManyField(Ganre)
    
    def __str__(self):
        return self.title
    
class Season(models.Model):
    anime = models.ForeignKey(Anime, on_delete=models.CASCADE, related_name="seasons")
    number = models.IntegerField()

    class Meta:
        unique_together = ["anime", "number"]  # Bir anime'da bir xil season bo'lmasin

    def __str__(self):
        return f"{self.anime.title} Season {self.number}"

    
