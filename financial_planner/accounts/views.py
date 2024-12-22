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
from django.utils.dateparse import parse_date  # Ensure this is imported
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

@login_required
def notification(request):
    # Fetch all expenses for the logged-in user
    user_expenses = Expense.objects.filter(user=request.user)

    # Calculate total expenses
    total_expenses = user_expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    # Get the user's profile and calculate total budget
    profile = getattr(request.user, 'profile', None)
    total_budget = 0
    total_food_budget = profile.food_budget or 0
    total_utilities_budget = profile.utilities_budget or 0
    total_entertainment_budget = profile.entertainment_budget or 0
    total_others_budget = profile.others_budget or 0
    
    if profile:
        total_budget = (
            total_food_budget +
            total_utilities_budget +
            total_entertainment_budget +
            total_others_budget
        )

    # Calculate total expenses for each category
    total_food_expenses = user_expenses.filter(category='Food').aggregate(Sum('amount'))['amount__sum'] or 0
    total_utilities_expenses = user_expenses.filter(category='Utilities').aggregate(Sum('amount'))['amount__sum'] or 0
    total_entertainment_expenses = user_expenses.filter(category='Entertainment').aggregate(Sum('amount'))['amount__sum'] or 0
    total_others_expenses = user_expenses.filter(category='Others').aggregate(Sum('amount'))['amount__sum'] or 0

    # Calculate progress bar widths for each category
    def calculate_progress_bar_width(expenses, budget):
        return round((expenses / budget) * 100, 2) if budget > 0 else 0

    progress_bar_width_food = calculate_progress_bar_width(total_food_expenses, total_food_budget)
    progress_bar_width_utilities = calculate_progress_bar_width(total_utilities_expenses, total_utilities_budget)
    progress_bar_width_entertainment = calculate_progress_bar_width(total_entertainment_expenses, total_entertainment_budget)
    progress_bar_width_others = calculate_progress_bar_width(total_others_expenses, total_others_budget)

    # Calculate overall progress for Expense vs Budget
    overall_progress = calculate_progress_bar_width(total_expenses, total_budget)

    # Determine progress classes based on the widths
    def get_progress_class(progress_bar_width):
        if progress_bar_width < 50:
            return 'progress-bar-low'
        elif progress_bar_width < 80:
            return 'progress-bar-medium'
        else:
            return 'progress-bar-high'

    progress_class_food = get_progress_class(progress_bar_width_food)
    progress_class_utilities = get_progress_class(progress_bar_width_utilities)
    progress_class_entertainment = get_progress_class(progress_bar_width_entertainment)
    progress_class_others = get_progress_class(progress_bar_width_others)
    progress_class_overall = get_progress_class(overall_progress)

    # Pass data to the context
    context = {
        'total_budget': total_budget,
        'total_expenses': total_expenses,
        'total_food_budget': total_food_budget,
        'total_utilities_budget': total_utilities_budget,
        'total_entertainment_budget': total_entertainment_budget,
        'total_others_budget': total_others_budget,
        'total_food_expenses': total_food_expenses,
        'total_utilities_expenses': total_utilities_expenses,
        'total_entertainment_expenses': total_entertainment_expenses,
        'total_others_expenses': total_others_expenses,
        'progress_bar_width_food': progress_bar_width_food,
        'progress_bar_width_utilities': progress_bar_width_utilities,
        'progress_bar_width_entertainment': progress_bar_width_entertainment,
        'progress_bar_width_others': progress_bar_width_others,
        'progress_bar_width_overall': overall_progress,
        'progress_class_food': progress_class_food,
        'progress_class_utilities': progress_class_utilities,
        'progress_class_entertainment': progress_class_entertainment,
        'progress_class_others': progress_class_others,
        'progress_class_overall': progress_class_overall,
    }

    # Render the template with context
    return render(request, 'accounts/notification.html', context)

@login_required
def alerts(request):
    # Fetch all expenses for the logged-in user
    user_expenses = Expense.objects.filter(user=request.user)

    # Get the user's profile and calculate total budget
    profile = getattr(request.user, 'profile', None)
    total_food_budget = float(profile.food_budget) if profile and profile.food_budget else 0
    total_utilities_budget = float(profile.utilities_budget) if profile and profile.utilities_budget else 0
    total_entertainment_budget = float(profile.entertainment_budget) if profile and profile.entertainment_budget else 0
    total_others_budget = float(profile.others_budget) if profile and profile.others_budget else 0
    
    # Calculate total expenses for each category
    total_food_expenses = user_expenses.filter(category='Food').aggregate(Sum('amount'))['amount__sum'] or 0
    total_utilities_expenses = user_expenses.filter(category='Utilities').aggregate(Sum('amount'))['amount__sum'] or 0
    total_entertainment_expenses = user_expenses.filter(category='Entertainment').aggregate(Sum('amount'))['amount__sum'] or 0
    total_others_expenses = user_expenses.filter(category='Others').aggregate(Sum('amount'))['amount__sum'] or 0

    # Define thresholds for warning and alert status
    warning_threshold_min = 0.60  # 70% of the budget
    warning_threshold_max = 0.99  # 99% of the budget
    alert_threshold = 1.0         # 100% of the budget

    # Determine status for each category
    def get_status(expenses, budget):
        if expenses >= budget * alert_threshold:
            return 'alert'
        elif expenses >= budget * warning_threshold_min and expenses <= budget * warning_threshold_max:
            return 'warning'
        return ''

    food_status = get_status(total_food_expenses, total_food_budget)
    utilities_status = get_status(total_utilities_expenses, total_utilities_budget)
    entertainment_status = get_status(total_entertainment_expenses, total_entertainment_budget)
    others_status = get_status(total_others_expenses, total_others_budget)

    # Pass data to the context
    context = {
        'total_food_budget': total_food_budget,
        'total_utilities_budget': total_utilities_budget,
        'total_entertainment_budget': total_entertainment_budget,
        'total_others_budget': total_others_budget,
        'total_food_expenses': total_food_expenses,
        'total_utilities_expenses': total_utilities_expenses,
        'total_entertainment_expenses': total_entertainment_expenses,
        'total_others_expenses': total_others_expenses,
        'food_status': food_status,
        'utilities_status': utilities_status,
        'entertainment_status': entertainment_status,
        'others_status': others_status,
    }

    # Render the template with context
    return render(request, 'accounts/alerts.html', context)


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

    # Total expenses for the speedometer
    total_expenses = user_expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    # Calculate total budget by summing the 4 fields
    profile = getattr(request.user, 'profile', None)
    total_budget = 0
    if profile:
        total_budget = (
            (profile.food_budget or 0) +
            (profile.entertainment_budget or 0) +
            (profile.utilities_budget or 0) +
            (profile.others_budget or 0)
        )

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

def set_budget(request):
    if request.method == 'GET':
        try:
            user_profile = request.user.profile
            data = {
                'food_budget': user_profile.food_budget,
                'entertainment_budget': user_profile.entertainment_budget,
                'utilities_budget': user_profile.utilities_budget,
                'others_budget': user_profile.others_budget,
            }
            return JsonResponse({'success': True, 'data': data})
        except Profile.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Profile not found.'}, status=404)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            food_budget = data.get('food_budget')
            entertainment_budget = data.get('entertainment_budget')
            utilities_budget = data.get('utilities_budget')
            others_budget = data.get('others_budget')

            if not all([food_budget is not None, entertainment_budget is not None, utilities_budget is not None, others_budget is not None]):
                return JsonResponse({'success': False, 'message': 'All budget fields are required.'}, status=400)

            user_profile = request.user.profile
            user_profile.food_budget = food_budget
            user_profile.entertainment_budget = entertainment_budget
            user_profile.utilities_budget = utilities_budget
            user_profile.others_budget = others_budget
            user_profile.save()

            return JsonResponse({'success': True, 'message': 'Budgets set successfully.'})
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
    categories = [choice[0] for choice in Expense.CATEGORY_CHOICES]
    return render(request, 'accounts/view_expenses.html', {'expenses': expenses, 'categories': categories})


@login_required
def get_categories(request):
    categories = [choice[0] for choice in Expense.CATEGORY_CHOICES]
    return JsonResponse({'categories': categories})


def filter_expenses(request):
    category = request.GET.get('category', 'All')
    start_date = request.GET.get('start_date', None)
    end_date = request.GET.get('end_date', None)

    filtered_expenses = Expense.objects.filter(user=request.user)

    if category != 'All':
        filtered_expenses = filtered_expenses.filter(category=category)

    if start_date:
        start_date_parsed = parse_date(start_date)
        if start_date_parsed:
            filtered_expenses = filtered_expenses.filter(date__gte=start_date_parsed)

    if end_date:
        end_date_parsed = parse_date(end_date)
        if end_date_parsed:
            filtered_expenses = filtered_expenses.filter(date__lte=end_date_parsed)

    # Prepare JSON response
    expenses_data = [
        {
            "id": expense.id,
            "date": expense.date.strftime('%b %d %Y'),
            "description": expense.description,
            "amount": str(expense.amount),
            "category": expense.category,
        }
        for expense in filtered_expenses
    ]

    return JsonResponse({"expenses": expenses_data})


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
