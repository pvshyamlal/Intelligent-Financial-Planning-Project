from django.db import models
from django.contrib.auth.models import User

class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="expenses")
    date = models.DateField()
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.description} - {self.amount} INR"
