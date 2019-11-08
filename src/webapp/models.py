from itertools import chain

# import geolocator as geolocator
from django.db import models
from jsonfield import JSONField

from geopy import distance
import datetime as dt
from datetime import date
import calendar
from geopy.geocoders import Nominatim
from django.conf import settings
from googleplaces import GooglePlaces, types
import time
import populartimes

google_places = GooglePlaces(settings.GOOGLE_PLACES_API_KEY)

onboard = False


class VenueManager(object):

    def is_google_cool(self):
        return False

    def get_top_venues(self, address, preferences):
        global onboard
        geolocator = Nominatim()
        location = geolocator.geocode(address, addressdetails=True)
        radius = preferences['radius']
        wait_time = preferences["wait_time"]

        if not onboard and location is not None:
            onboard = True
            coord_one, coord_two = self.get_coordinates(geolocator, location)
            results = populartimes.get(settings.GOOGLE_PLACES_API_KEY, [types.TYPE_BAR], coord_one, coord_two, 20,
                                       radius, False)
            for result in results:
                print("Creating " + result["name"])
                if "current_popularity" not in result:
                    result["current_popularity"] = 0
                if "time_wait" not in result:
                    result["time_wait"] = 0
                Venue.objects.create(name=result["name"], address=result["address"],
                                     coordinates=result['coordinates'],
                                     place_id=result["id"], rating=result["rating"], rating_n=result["rating_n"],
                                     current_popularity=result["current_popularity"], wait_time=result["time_wait"],
                                     populartimes=result["populartimes"])

        venues = Venue.objects.all()
        venues = filter(lambda x: self.get_wait_time(x) <= wait_time, venues)
        venues = filter(lambda x: self.distance_to(location, radius, x), venues)
        venues = sorted(venues, key=lambda i: self.get_popularity(i), reverse=True)
        venues = sorted(venues, key=lambda i: i.rating, reverse=True)
        return list(venues)

    def get_coordinates(self, geolocator, location):
        coord_one = (location.latitude, location.longitude)
        city = location.raw["address"]["city"]
        country = location.raw["address"]["country"]
        center_of_city = geolocator.geocode(city + ',' + country)
        cx = location.latitude + 2 * (center_of_city.latitude - location.latitude)
        cy = location.longitude + 2 * (center_of_city.longitude - location.longitude)
        coord_two = (cx, cy)
        return coord_one, coord_two

    def distance_to(self, location, radius, venue):
        coord_one = (location.latitude, location.longitude)
        coord_two = (venue.coordinates["lat"], venue.coordinates["lng"])
        return radius > distance.vincenty(coord_one, coord_two).meters

    def get_popularity(self, venue):
        closest_hour = dt.datetime.now().hour
        my_date = date.today()
        weekday = calendar.day_name[my_date.weekday()]
        times = venue.populartimes
        for day in times:
            if "name" in day and day["name"] == weekday:
                return day["data"][closest_hour]
            else:
                return 0

    def get_wait_time(self, venue):
        closest_hour = dt.datetime.now().hour
        my_date = date.today()
        weekday = calendar.day_name[my_date.weekday()]
        times = venue.wait_time
        if type(times) == int:
            return times
        for day in times:
            if "name" in day and day["name"] == weekday:
                return day["data"][closest_hour]
            else:
                return 0

    # def aggregate(self, query_result):
    # if self.is_google_cool():
    #     query_result = google_places.nearby_search(lat_lng={"lat": location.latitude, "lng": location.longitude},
    #                                                radius=radius, types=[types.TYPE_BAR])
    #     venues = self.aggregate(query_result)
    #     aggregated = []
    #     for place in query_result.places:
    #         try:
    #             venue = Venue.objects.get(place_id=place.place_id)
    #             mixed = {"name": place.name, "address": place.formatted_address, "number": place.local_phone_number,
    #                      "current_popularity": venue.current_popularity, "time_wait": venue.time_spent,
    #                      "popular_times": venue.popular_times}
    #             aggregated.append(mixed)
    #         except Venue.DoesNotExist:
    #             pass
    #
    #     if query_result.has_next_page_token:
    #         query_result_next_page = google_places.nearby_search(pagetoken=query_result.next_page_token)
    #         return aggregated.extend(self.aggregate(query_result_next_page))
    #     return aggregated


class UserPreference(models.Model):
    username = models.CharField(max_length=50)
    email = models.CharField(max_length=50)
    venue_type = models.CharField(max_length=50, default='ALL')
    music_type = models.CharField(max_length=50, default='ALL')
    wait_time = models.IntegerField(default=30)
    radius = models.IntegerField(default=5000)


# Types = "Restaurant, food, point_of_interest", "establishment"

class Venue(models.Model):
    place_id = models.CharField(max_length=200, default=None)
    name = models.CharField(max_length=50, default="")
    address = models.CharField(max_length=100, default="")
    coordinates = JSONField(default={})
    # types = models.CharField(max_length=50, default)
    rating = models.FloatField(default=0)
    rating_n = models.IntegerField(default=0)
    wait_time = JSONField(default={})
    current_popularity = models.IntegerField(default=0)
    populartimes = JSONField(default={})

    def get_top_nearby_venues(self, address, request):
        if not address:
            return Venue.objects.none()
        try:
            user_preferences = UserPreference.objects.get(username=request.user)
        except UserPreference.DoesNotExist:
            user_preferences = {"Venue": "ALL", "Music Type": "ALL", "radius": 50000, "wait_time": 30}

        ranked_venues = VenueManager().get_top_venues(address, user_preferences)
        none_qs = Venue.objects.none()
        return list(chain(none_qs, ranked_venues))
