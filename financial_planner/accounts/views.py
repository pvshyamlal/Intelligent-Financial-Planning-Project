from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from .forms import UserRegistrationForm, ExpenseForm, ProfileForm
from .models import Expense, Profile
from .models import Profile
import logging
from django.contrib.auth.hashers import check_password
from django.views.decorators.csrf import csrf_exempt
from django.contrib.messages import get_messages
from django.db.models import Sum
import json

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
            user.set_password(form.cleaned_data['password'])  # Set password correctly
            user.save()  # Save the user to the database

            # Check if Profile already exists, if not, create one
            if not hasattr(user, 'profile'):
                Profile.objects.create(user=user)

            messages.success(request, 'Registration successful! Please log in.')
            return redirect('login')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    # Clear stale messages
    clear_stale_messages(request)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            # Check if username exists
            if not User.objects.filter(username=username).exists():
                messages.error(request, 'Username is incorrect. Please try again.')
                return render(request, 'accounts/login.html')

            # Authenticate user
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Login the user
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('/profile?first_login=true')  # Redirect to profile page after login
            else:
                messages.error(request, 'Password is incorrect. Please try again.')

        except Exception as e:
            messages.error(request, 'Something went wrong. Please refresh the page and try again.')
            print(f"Error: {e}")

    return render(request, 'accounts/login.html')

@login_required
def edit_profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        username = request.POST.get('username')
        if username:
            request.user.username = username
            request.user.save()

            # Return a JSON response to close the form
            return JsonResponse({'success': True, 'message': 'Username updated successfully!'})

        return JsonResponse({'success': False, 'message': 'Failed to update username.'})

    return render(request, 'accounts/edit_profile.html', {'user': request.user, 'profile': profile})

@login_required
def dashboard(request):
    # Fetch all expenses for the logged-in user
    user_expenses = Expense.objects.filter(user=request.user)

    # Get the latest 5 expenses for the tile
    latest_expenses = user_expenses.order_by('-date')[:5]

    # Aggregate total amounts per category for the bar graph
    expenses_by_category = user_expenses.values('category').annotate(total=Sum('amount'))

    # Extract categories and amounts for Chart.js
    categories = [item['category'] for item in expenses_by_category]
    amounts = [float(item['total']) for item in expenses_by_category]

    # Total expenses and budget for the speedometer
    total_expenses = user_expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    total_budget = request.user.profile.budget if hasattr(request.user, 'profile') else 0

    context = {
        'categories': json.dumps(categories),
        'amounts': json.dumps(amounts),
        'total_expenses': total_expenses,
        'total_budget': total_budget,
        'latest_expenses': latest_expenses,  # Only latest 5 for the table tile
    }

    return render(request, 'accounts/dashboard.html', context)

logger = logging.getLogger(__name__)
@login_required
def update_username(request):
    try:
        if request.method == "POST" and request.is_ajax():
            new_username = request.POST.get("username")
            if new_username:
                # Check if the username already exists
                if User.objects.filter(username=new_username).exists():
                    return JsonResponse({
                        "success": False, 
                        "message": "This username is already taken. Please try a different one."
                    })

                # Update the user's username
                request.user.username = new_username
                request.user.save()
                return JsonResponse({
                    "success": True, 
                    "message": "Username updated successfully!"
                })

            return JsonResponse({
                "success": False, 
                "message": "Invalid username."
            })
        return JsonResponse({
            "success": False, 
            "message": "Invalid request."
        })
    except Exception as e:
        logger.error(f"Error in update_username: {e}")
        return JsonResponse({
            "success": False, 
            "message": "An unexpected error occurred. Please try again later."
        })
    
@login_required
def change_password(request):
    if request.method == 'POST':
        # Ensure user is authenticated
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'message': 'User not authenticated.'})

        # Get old and new passwords from the request
        data = json.loads(request.body)  # Extract data from the JSON body
        old_password = data.get('old_password')
        new_password = data.get('new_password')

        # Ensure old password is correct
        if not request.user.check_password(old_password):
            return JsonResponse({'success': False, 'message': 'Incorrect old password.'})

        if old_password == new_password:
            return JsonResponse({'success': False, 'message': 'New password cannot be the same as old password.'})

        # Set the new password
        user = request.user
        user.set_password(new_password)
        user.save()

        # Update session so user doesn't get logged out
        update_session_auth_hash(request, user)

        return JsonResponse({'success': True, 'message': 'Password updated successfully!'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@login_required
@csrf_exempt  # Only if necessary; ideally, use CSRF tokens
def set_budget(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            budget_amount = data.get('budget')

            if budget_amount is None:
                return JsonResponse({'success': False, 'message': 'Budget amount is required.'}, status=400)

            # Assuming you have a profile model with a budget field, save the budget
            user_profile = request.user.profile
            user_profile.budget = budget_amount
            user_profile.save()

            return JsonResponse({'success': True, 'message': 'Budget set successfully.'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid data.'}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

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
