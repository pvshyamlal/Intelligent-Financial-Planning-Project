from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from .forms import UserRegistrationForm, ExpenseForm
from .models import Expense
from django.views.decorators.csrf import csrf_exempt
from django.contrib.messages import get_messages
from django.db.models import Sum
import json
from django.middleware import csrf as CsrfViewMiddleware

# Helper function to clear stale messages
def clear_stale_messages(request):
    storage = get_messages(request)
    for _ in storage:
        pass

def home(request):
    return render(request, 'accounts/home.html')

@login_required
def profile(request):
    if request.GET.get('first_login'):
        messages.success(request, f"Welcome back, {request.user.username}!")
    return render(request, 'accounts/profile.html')

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, 'Registration successful! Please log in.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    clear_stale_messages(request)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
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

        except CsrfViewMiddleware.CsrfTokenMissing:
            messages.error(request, 'Something went wrong. Please refresh the page and try again.')

    return render(request, 'accounts/login.html')

@login_required
def add_expenses(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            messages.success(request, 'Expense added successfully!')
            return redirect('add_expenses')
    else:
        form = ExpenseForm()

    return render(request, 'accounts/add_expenses.html', {'form': form})

@login_required
def view_expenses(request):
    clear_stale_messages(request)

    expenses = Expense.objects.filter(user=request.user)
    return render(request, 'accounts/view_expenses.html', {'expenses': expenses})

@login_required
def financial_reports(request):
    # Filter expenses for the logged-in user
    user_expenses = Expense.objects.filter(user=request.user)

    # Aggregate total amounts per category
    expenses_by_category = user_expenses.values('category').annotate(total=Sum('amount'))

    # Extract categories and amounts
    categories = []
    amounts = []

    for expense in expenses_by_category:
        category = expense['category']
        total = expense['total']

        # Include all valid categories; handle "Others" separately
        if category in ['Food', 'Utilities', 'Entertainment', 'Others']:
            categories.append(category)
            amounts.append(float(total))  # Convert Decimal to float

    # Calculate totals and averages
    total_expense = user_expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    # Get the count of unique dates
    distinct_dates = user_expenses.values('date').distinct().count()

    # Calculate average as sum of amounts / number of unique dates
    average_daily_expense = total_expense / distinct_dates if distinct_dates > 0 else 0

    context = {
        'categories': json.dumps(categories),  # Serialize categories for JavaScript
        'amounts': json.dumps(amounts),        # Serialize amounts for JavaScript
        'total_expense': total_expense,
        'average_daily_expense': average_daily_expense,
    }
    return render(request, 'accounts/financial_reports.html', context)
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

@login_required
@csrf_exempt
def delete_expense(request, expense_id):
    try:
        expense = Expense.objects.get(id=expense_id, user=request.user)
        expense.delete()
        return JsonResponse({"success": True}, status=200)
    except Expense.DoesNotExist:
        return JsonResponse({"success": False, "error": "Expense not found"}, status=404)
