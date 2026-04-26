from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ExtendedSignUpForm, BusinessProfileForm
from .models import BusinessProfile


def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    return render(request, 'landing.html')


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    if request.method == 'POST':
        form = ExtendedSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f"Welcome to Biz-Light, {user.username}! Let's set up your business profile.")
            return redirect('accounts:onboarding')
    else:
        form = ExtendedSignUpForm()
    features = [
        'AI-powered business summaries',
        'Real-time inventory alerts',
        'Financial KPI tracking',
        'Smart reorder recommendations',
    ]
    return render(request, 'registration/signup.html', {'form': form, 'features': features})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('dashboard:index')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})


@login_required
def onboarding_view(request):
    # Allow re-visiting to update the profile
    try:
        existing_profile = request.user.business_profile
    except BusinessProfile.DoesNotExist:
        existing_profile = None

    if request.method == 'POST':
        form = BusinessProfileForm(request.POST, instance=existing_profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, "Business profile saved successfully!")
            return redirect('dashboard:index')
    else:
        form = BusinessProfileForm(instance=existing_profile)

    return render(request, 'registration/onboarding.html', {'form': form})


@login_required
def profile_view(request):
    profile = getattr(request.user, 'business_profile', None)
    return render(request, 'registration/profile.html', {'profile': profile})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out successfully.")
    return redirect('accounts:landing')
