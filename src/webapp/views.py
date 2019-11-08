from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.contrib.auth import logout as django_logout
import json
from django.contrib.auth.decorators import login_required
from store.settings import SOCIAL_AUTH_AUTH0_DOMAIN, SOCIAL_AUTH_AUTH0_KEY
from .models import Venue, UserPreference
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .forms import SearchForm
from django.conf import settings


def index(request):
    page = request.GET.get('page', 1)

    print(request.GET)

    print(page)

    address = None
    if request.method == 'POST':  # If the form has been submitted...
        address = request.POST["where_load"]  # A form bound to the POST data
    elif request.method == 'GET':
        try:
            address = request.GET['search']
        except:
            pass

    paginator = Paginator(Venue().get_top_nearby_venues(address, request), 10)
    try:
        venues = paginator.page(page)
    except PageNotAnInteger:
        venues = paginator.page(1)
    except EmptyPage:
        venues = paginator.page(paginator.num_pages)

    context = {
        "venues": venues,
        "search": address,
        "api_key": settings.GOOGLE_PLACES_API_KEY,
        "form": SearchForm
    }
    return render(request, 'index.html', context=context)


@login_required
def profile(request):
    user = request.user
    auth0user = user.social_auth.get(provider='auth0')
    try:
        user_preferences = UserPreference.objects.get(username=request.user)
    except UserPreference.DoesNotExist:
        user_preferences = {"Venue": "ALL", "Music Type": "ALL"}

    userdata = {
        'user_id': auth0user.uid,
        'name': user.first_name,
        'picture': auth0user.extra_data['picture']
    }

    return render(request, 'profile.html', {
        'auth0User': auth0user,
        'userdata': json.dumps(userdata, indent=4),
        'userPreferences': user_preferences
    })


def logout(request):
    django_logout(request)
    domain = SOCIAL_AUTH_AUTH0_DOMAIN
    client_id = SOCIAL_AUTH_AUTH0_KEY
    return_to = 'http://localhost:8000'
    return HttpResponseRedirect(f'https://{domain}/v2/logout?client_id={client_id}&returnTo={return_to}')
