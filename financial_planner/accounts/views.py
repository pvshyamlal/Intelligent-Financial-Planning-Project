from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from .forms import UserRegistrationForm, ExpenseForm
from .models import Expense
from django.db.models import Sum
import json


# Helper function to clear stale messages
def clear_stale_messages(request):
    storage = messages.get_messages(request)
    for _ in storage:
        pass


# Home View
def home(request):
    return render(request, 'accounts/home.html')


# Profile View
@login_required
def profile(request):
    if request.GET.get('first_login'):
        messages.success(request, f"Welcome back, {request.user.username}!")
    return render(request, 'accounts/profile.html')


# Register View
def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Check for unique username
            username = form.cleaned_data.get('username')
            if User.objects.filter(username=username).exists():
                form.add_error('username', 'This username is already taken. Please choose another.')
            else:
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.save()
                messages.success(request, 'Registration successful! Please log in.')
                return redirect('login')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


# Login View
def login_view(request):
    clear_stale_messages(request)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not User.objects.filter(username=username).exists():
            messages.error(request, 'Username is incorrect. Please try again.')
            return render(request, 'accounts/login.html')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('/profile?first_login=true')
        else:
            messages.error(request, 'Password is incorrect. Please try again.')

    return render(request, 'accounts/login.html')


# Add Expenses View
@login_required
def add_expenses(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            messages.success(request, 'Expense added successfully!')
            return redirect('view_expenses')
    else:
        form = ExpenseForm()

    return render(request, 'accounts/add_expenses.html', {'form': form})


# View Expenses View
@login_required
def view_expenses(request):
    clear_stale_messages(request)
    expenses = Expense.objects.filter(user=request.user).order_by('-date')
    return render(request, 'accounts/view_expenses.html', {'expenses': expenses})


# Financial Reports View
@login_required
def financial_reports(request):
    user_expenses = Expense.objects.filter(user=request.user)
    expenses_by_category = user_expenses.values('category').annotate(total=Sum('amount'))

    categories = [expense['category'] for expense in expenses_by_category]
    amounts = [float(expense['total']) for expense in expenses_by_category]

    total_expense = user_expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    distinct_dates = user_expenses.values('date').distinct().count()
    average_daily_expense = total_expense / distinct_dates if distinct_dates > 0 else 0

    context = {
        'categories': json.dumps(categories),
        'amounts': json.dumps(amounts),
        'total_expense': total_expense,
        'average_daily_expense': average_daily_expense,
    }
    return render(request, 'accounts/financial_reports.html', context)


# Edit Expense View
@login_required
def edit_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, user=request.user)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense updated successfully!")
            return redirect('view_expenses')
    else:
        form = ExpenseForm(instance=expense)

    return render(request, 'accounts/edit_expense.html', {'form': form, 'expense': expense})


# Delete Expense View
@login_required
def delete_expense(request, expense_id):
    try:
        expense = get_object_or_404(Expense, id=expense_id, user=request.user)
        expense.delete()
        messages.success(request, "Expense deleted successfully!")
        return redirect('view_expenses')
    except Expense.DoesNotExist:
        messages.error(request, "The expense you are trying to delete does not exist.")
        return redirect('view_expenses')
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect('view_expenses')
