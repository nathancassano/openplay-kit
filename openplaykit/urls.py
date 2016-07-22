"""
Copyright 2016 by Bubble Zap, LLC
See the LICENSE file distributed with this work for additional
information regarding copyright ownership. The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

# The views used below are normally mapped in django.contrib.admin.urls.py
# This URLs file is used to provide a reliable view deployment for test purposes.
# It is also provided as a convenience to those who want to deploy these URLs
# elsewhere.

from django.conf.urls import patterns, url
from openplaykit import views

urlpatterns = patterns('',
    url(r'^LoginWithPlayFab$', views.LoginWithPlayFab, name='LoginWithPlayFab'),
    url(r'^RegisterPlayFabUser$', views.RegisterPlayFabUser, name='RegisterPlayFabUser'),
    url(r'^UpdateUserTitleDisplayName$', views.UpdateUserTitleDisplayName, name='UpdateUserTitleDisplayName'),
    url(r'^LoginWithAndroidDeviceID$', views.LoginWithAndroidDeviceID, name='LoginWithAndroidDeviceID'),
    url(r'^LoginWithIOSDeviceID$', views.LoginWithIOSDeviceID, name='LoginWithIOSDeviceID'),
    url(r'^AddUsernamePassword$', views.AddUsernamePassword, name='AddUsernamePassword'),
    url(r'^UpdateEmailAddress$', views.UpdateEmailAddress, name='UpdateEmailAddress'),
    url(r'^UpdatePassword$', views.UpdatePassword, name='UpdatePassword'),
    url(r'^UpdateUserTitleDisplayName$', views.UpdateUserTitleDisplayName, name='UpdateUserTitleDisplayName'),
    url(r'^UpdateUserData$', views.UpdateUserData, name='UpdateUserData'),
    url(r'^GetUserData$', views.GetUserData, name='GetUserData'),
    url(r'^LinkAndroidDeviceID$', views.LinkAndroidDeviceID, name='LinkAndroidDeviceID'),
    url(r'^GetCatalogItems$', views.GetCatalogItems, name='GetCatalogItems'),
    url(r'^ConsumeItem$', views.ConsumeItem, name='ConsumeItem'),
    url(r'^PurchaseItem$', views.PurchaseItem, name='PurchaseItem'),
    url(r'^ValidateGooglePlayPurchase$', views.ValidateGooglePlayPurchase, name='ValidateGooglePlayPurchase'),
    url(r'^ValidateIOSReceipt$', views.ValidateIOSReceipt, name='ValidateIOSReceipt'),
    url(r'^GetUserInventory$', views.GetUserInventory, name='GetUserInventory'),
    url(r'^GetTitleNews$', views.GetTitleNews, name='GetTitleNews'),
    url(r'^GetTitleData$', views.GetTitleData, name='GetTitleData'),
    url(r'^AddUserVirtualCurrency$', views.AddUserVirtualCurrency, name='AddUserVirtualCurrency'),
    url(r'^SubtractUserVirtualCurrency$', views.SubtractUserVirtualCurrency, name='SubtractUserVirtualCurrency'),
    url(r'^LinkFacebookAccount$', views.LinkFacebookAccount, name='LinkFacebookAccount'),
    url(r'^ResetUser$', views.ResetUser, name='ResetUser'),
)
