from django import forms


class SearchForm(forms.Form):
    where_load = forms.CharField(max_length=100,
                                 widget=forms.TextInput(
                                     attrs={"style": 'font-size: 25px; width: 100%;', 'id': "autocomplete",
                                            "class": "uk-search-input",
                                            "onFocus": "geolocate()",
                                            "placeholder": "Type your location..."}))
