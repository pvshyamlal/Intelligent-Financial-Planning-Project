from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    food_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    entertainment_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    utilities_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    others_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    additional_info = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.user.username

class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('Food', 'Food'),
        ('Utilities', 'Utilities'),
        ('Entertainment', 'Entertainment'),
        ('Others', 'Others'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="expenses")
    date = models.DateField()
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Others')

    def __str__(self):
        return f"{self.description} - {self.amount} INR"
