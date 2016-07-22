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

import re
import uuid
import datetime

from django.db import models

from django.contrib.auth.hashers import (check_password, make_password)
from django.utils import timezone
from django.core import validators
from django.core import exceptions

def getUUID():
    return str(uuid.uuid4())

class UserAccount(models.Model):
    UUID = models.CharField(max_length=36, unique=True, default=getUUID )
    DisplayName = models.CharField(max_length=32)
    SessionTicket = models.CharField(max_length=36, unique=True, default=getUUID )
    Origination = models.CharField(max_length=16)
    Created = models.DateTimeField(default=timezone.now)
    LastLogin = models.DateTimeField(default=timezone.now)
    FirstLogin = models.DateTimeField(default=timezone.now)
    Active = models.BooleanField(default=True)
    Annotations = models.TextField(blank=True)
        
    def loginRefresh(self):
        # Set first login datetime
        if self.FirstLogin == datetime.datetime.min:
            self.FirstLogin = timezone.now()
        self.LastLogin = timezone.now()
        return self.SessionTicket
    
    def getUserCurrencies(self):
        return UserCurrency.objects.filter(Account=self.pk)
    
    def getCurrencyByCode(self, currencyCode):
        try:
            currency = CurrencyType.objects.get(CurrencyCode=currencyCode)
        except exceptions.ObjectDoesNotExist:
            raise Exception('Currency does not exist')
        return self.getCurrency(currency)
    
    def getCurrency(self, currency):
        try:
            currencyUser = UserCurrency.objects.get(Account=self, Currency=currency)
        except exceptions.ObjectDoesNotExist:
            currencyUser = UserCurrency.objects.create(Account=self, Currency=currency, Amount=currency.InitialDeposit)
            
        return currencyUser
    
    def getUserItems(self):
        return UserItems.objects.filter(Account=self).exclude(RemainingUses=0)

    def __str__(self):
        return ' '.join([self.UUID, self.DisplayName])

# Future replacement for UserAccount.SessionTicket
class UserSession(models.Model):
    SessionTicket = models.CharField(max_length=36, unique=True, default=getUUID )
    Account = models.ForeignKey(UserAccount)
    Created = models.DateTimeField(default=timezone.now)

class ManagedUserAccount(models.Model):
    Username = models.CharField(max_length=30, unique=True,
        help_text='Required. 30 characters or fewer. Letters, numbers and @/./+/-/_ characters',
        validators=[validators.RegexValidator(re.compile('^[\w.@+-]+$'), 'Enter a valid username.', 'invalid')])
    Password = models.CharField(max_length=128)
    Email = models.EmailField()
    Account = models.ForeignKey(UserAccount)
    
    def setPassword(self, raw_password):
        self.Password = make_password(raw_password)

    def checkPassword(self, raw_password):
        """
        Returns a boolean of whether the raw_password was correct. Handles
        hashing formats behind the scenes.
        """
        def setter(raw_password):
            self.setPassword(raw_password)
            self.save(update_fields=['Password'])
        return check_password(raw_password, self.Password, setter)
    
    @staticmethod
    def isUniqueEmail(email):
        try:
            ManagedUserAccount.objects.get(Email=email)
        except exceptions.ObjectDoesNotExist:
            return True
        except exceptions.MultipleObjectsReturned:
            return False
        return False

    def __str__(self):
        if not self.Username:
            return 'Unset'
        return self.Username
 
class UserData(models.Model):
    PERM_PUBLIC = 1
    PERM_PRIVATE = 0
    PERM_CHOICES = ( (PERM_PUBLIC, 'Public'), (PERM_PRIVATE, 'Private') )

    Key = models.CharField(max_length=128)
    Data = models.TextField()
    Permission = models.IntegerField(choices=PERM_CHOICES, default=PERM_PUBLIC)
    LastUpdated = models.DateTimeField(default=timezone.now, auto_now=True)
    Account = models.ForeignKey(UserAccount)

    def __str__(self):
        return ' '.join([self.Key, self.Account.UUID])   
   
class AndroidDevice(models.Model):
    AndroidDeviceId = models.CharField(max_length=256, primary_key=True)
    OS = models.CharField(max_length=16)
    DeviceName = models.CharField(max_length=128)
    Account = models.ForeignKey(UserAccount)

    def __str__(self):
        return ' '.join([self.AndroidDeviceId, self.DeviceName, '('+self.OS+')'])

class IOSDevice(models.Model):
    IOSDeviceId = models.CharField(max_length=256, primary_key=True)
    OS = models.CharField(max_length=4)
    DeviceModel = models.CharField(max_length=128)
    Account = models.ForeignKey(UserAccount)

    def __str__(self):
        return ' '.join([self.IOSDeviceId, self.OS, '('+self.DeviceModel+')'])

class GameCenterAccount(models.Model):
    PlayerId = models.CharField(max_length=128, primary_key=True)
    Account = models.ForeignKey(UserAccount)

class FaceBookAccount(models.Model):
    Account = models.ForeignKey(UserAccount)
    AccessToken = models.CharField(max_length=256)
    
class SteamAccount(models.Model):
    SteamTicket = models.CharField(max_length=128, primary_key=True)
    Account = models.ForeignKey(UserAccount)

class News(models.Model):
    Timestamp = models.DateTimeField(default=timezone.now)
    Title = models.CharField(max_length=128)
    Body = models.TextField()

class CurrencyType(models.Model):
    CurrencyCode = models.CharField(max_length=2, primary_key=True)
    InitialDeposit = models.IntegerField()
    Description = models.CharField(max_length=64)
    RemotelyMutable = models.BooleanField(default=True)
    DirectTransactionLimit = models.IntegerField(default=0)

    def __str__(self):
        return ' '.join([self.CurrencyCode, self.Description])

class UserCurrency(models.Model):
    Currency = models.ForeignKey(CurrencyType)
    Amount = models.IntegerField()
    Account = models.ForeignKey(UserAccount)
    LastUpdated = models.DateTimeField(default=timezone.now, auto_now=True)
    
    def canBuy(self, price):
        return price <= self.Account
    
    def debit(self, price):
        self.Amount = self.Amount - price
        self.save()

    def credit(self, price):
        self.Amount = self.Amount + price
        self.save() 

    def __str__(self):
        return self.Currency.CurrencyCode + ' (' + str(self.Amount) + ')'

class Catalog(models.Model):
    Name = models.CharField(max_length=32)
    IsDefault = models.BooleanField(default=False)
    Created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.Name

class CatalogItem(models.Model):
    ItemId = models.CharField(max_length=64)
    ItemClass = models.CharField(max_length=128, blank=True)
    DisplayName = models.CharField(max_length=128, blank=True)
    Description = models.CharField(max_length=256, blank=True)
    Tags = models.CharField(max_length=256, blank=True)
    UsageCount = models.IntegerField(default=0)
    UsagePeriod = models.IntegerField(default=0)
    ConsumeOnPurchase = models.BooleanField(default=False)
    IsStackable = models.BooleanField(default=False)
    IsTradeable = models.BooleanField(default=False)
    ItemImageUrl = models.URLField(max_length=256, blank=True)
    IsContainer = models.BooleanField(default=False)
    UnlockKey = models.CharField(max_length=32, blank=True)
    Catalog = models.ForeignKey(Catalog, null=False)

    def isConsumeable(self):
        return self.UsageCount > 0

    def getItemPrice(self, CurrencyCode ):
        currency = CurrencyType.objects.get(CurrencyCode=CurrencyCode)

        try:
            return ItemPrice.objects.filter(Item=self.pk, Currency=currency)[0]
        except exceptions.ObjectDoesNotExist:
            return None

    def getCatalogRepresentation(self):
        itemProps = {
            'ItemId': self.ItemId,
            'ItemClass': self.ItemClass,
            'CatalogVersion': self.Catalog.Name,
            'DisplayName': self.DisplayName,
            'Description': self.Description,
            'IsStackable': self.IsStackable,
            'IsTradable': self.IsStackable
        }

        itemPrices = self.getItemPrices()
        if itemPrices:
            itemProps['VirtualCurrencyPrices'] = { ip.Currency.CurrencyCode: ip.Price for ip in itemPrices }

        # If consumable
        if self.UsageCount > 0:
            consumable = {}
            if self.UsageCount > 0:
                consumable['UsageCount'] = self.UsageCount
            if self.UsagePeriod:
                consumable['UsagePeriod'] = self.UsagePeriod
            itemProps['Consumable'] = consumable
        
        bundleCurrencies = self.getCurrencyBundles()
        itemBundles = self.getItemBundles()

	# Attributes 
        attributes = self.getAttributes()
        if attributes:
            itemProps['Attributes'] = attributes

        # If bundle
        if bundleCurrencies or itemBundles:
            bundle = {}
            if bundleCurrencies:
                bundle['BundledVirtualCurrencies'] = { bc.Currency.CurrencyCode: bc.Amount for bc in bundleCurrencies } 
            if itemBundles:
                bundle['BundledItems'] = [i.BundledItem.ItemId for i in itemBundles]
                bundle['BundledItemsQuantity'] = [i.Quantity for i in itemBundles]
            itemProps['Bundle'] = bundle
        
        #itemProps['RealCurrencyPrices'] = {}

        return itemProps
    
    def getUserRepresentation(self):
        itemProps = {
            'ItemId': self.ItemId,
            'ItemInstanceId': str(self.pk),
            'ItemClass': self.ItemClass,
            'CatalogVersion': self.Catalog.Name,
            'UnitPrice': 0
        }
        return itemProps
    
    def getAttributes(self):
        return { i.Key: i.Value for i in ItemAttribute.objects.filter(Item=self.pk) }

    def getItemPrices(self):
        return ItemPrice.objects.filter(Item=self.pk)

    def assignToUser(self, userAccount, purchase=None):
        
        itemsAssigned = [self.getUserRepresentation()]
        
        # Calculate expiration
        if self.UsagePeriod <= 0:
            expiration = None
        else:
            expiration = datetime.datetime.now() + datetime.timedelta(seconds=self.UsagePeriod)
        
        # If item is durable
        if self.UsageCount <= 0:
            remainingUses = -1
        # Consumable
        else:
            if self.IsContainer or self.ConsumeOnPurchase == False:
                remainingUses = self.UsageCount
            else:
                remainingUses = 0

        UserItems.objects.create(Item=self, Account=userAccount, Purchase=purchase, RemainingUses=remainingUses, Expiration=expiration)
        
        # If item is not a container then consume and assign now
        if not self.IsContainer:
            itemBundles = self.getItemBundles()
            if itemBundles:
                for item in itemBundles:
                    itemsAssigned = itemsAssigned + item.assignToUser(userAccount, purchase)

            # Assign currencies
            if self.UsageCount >= 1:
                bundleCurrencies = self.getCurrencyBundles()
                if bundleCurrencies:
                    for currencyPayout in bundleCurrencies:
                        userCurrency = userAccount.getCurrency( currencyPayout.Currency )
                        userCurrency.credit( currencyPayout.Amount * self.UsageCount )
                        userCurrency.save()
                    
        return itemsAssigned
    
    def getCurrencyBundles(self):
        return BundleCurrency.objects.filter(Item = self.pk)
        
    def getItemBundles(self):
        return BundleItem.objects.filter(Item = self.pk)

    def __str__(self):
        return self.ItemId + ' (' + self.Catalog.Name + ')'

# The different costs for an item
class ItemPrice(models.Model):
    Price = models.IntegerField()
    Currency = models.ForeignKey(CurrencyType)
    Item = models.ForeignKey(CatalogItem)

    def __str__(self):
        return ' '.join([self.Currency.CurrencyCode, str(self.Price)])

# Items bundled with a parent item
class BundleItem(models.Model):
    Quantity = models.IntegerField(default=1)
    BundledItem = models.ForeignKey(CatalogItem, related_name='bundled_item')
    Item = models.ForeignKey(CatalogItem)

    def __str__(self):
        return self.BundledItem.ItemId + ('(' + str(self.Quantity) + ')' if self.Quantity > 1 else '')

# Currency given as a part of an item
class BundleCurrency(models.Model):
    Amount = models.IntegerField()
    Currency = models.ForeignKey(CurrencyType)
    Item = models.ForeignKey(CatalogItem)

    def __str__(self):
        return ' '.join([self.Currency.CurrencyCode, str(self.Amount)])

class ItemAttribute(models.Model):
    Key = models.CharField(max_length=128)
    Value = models.CharField(max_length=256)
    Item = models.ForeignKey(CatalogItem)

    def __str__(self):
        return ' '.join([self.Item.ItemId, self.Key])

class Purchase(models.Model):
    
    STATUS_CREATECART = 0
    STATUS_INIT = 1
    STATUS_APPROVED = 2
    STATUS_SUCCEEDED = 3
    STATUS_FAILEDBYPROVIDER = 4
    STATUS_DISPUTEPENDING = 5
    STATUS_REFUNDPENDING = 6
    STATUS_REFUNDED = 7
    STATUS_REFUNDFAILED = 8
    STATUS_CHARGEDBACK = 9
    STATUS_FAILEDBYUBER = 10
    STATUS_REVOKED = 11
    STATUS_TRADEPENDING = 12
    STATUS_TRADED = 13
    STATUS_UPGRADED = 14
    STATUS_STACKPENDING = 15
    STATUS_STACKED = 16
    STATUS_OTHER = 17
    STATUS_FAILED = 18

    STATUS_CHOICES = (
        (STATUS_CREATECART, 'CreateCart'),
        (STATUS_INIT, 'Init'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_SUCCEEDED, 'Succeeded'),
        (STATUS_FAILEDBYPROVIDER, 'FailedByProvider'),
        (STATUS_DISPUTEPENDING, 'DisputePending'),
        (STATUS_REFUNDPENDING, 'RefundPending'),
        (STATUS_REFUNDED, 'Refunded'),
        (STATUS_REFUNDFAILED, 'RefundFailed'),
        (STATUS_CHARGEDBACK, 'ChargedBack'),
        (STATUS_FAILEDBYUBER, 'FailedByUber'),
        (STATUS_REVOKED, 'Revoked'),
        (STATUS_TRADEPENDING, 'TradePending'),
        (STATUS_TRADED, 'Traded'),
        (STATUS_UPGRADED, 'Upgraded'),
        (STATUS_STACKPENDING, 'StackPending'),
        (STATUS_STACKED, 'Stacked'),
        (STATUS_OTHER, 'Other'),
        (STATUS_FAILED, 'Failed')
    )
    
    PROVIDER_NONE = 0
    PROVIDER_VIRTUALCURRENCY = 1
    PROVIDER_GOOGLEPLAY = 2
    PROVIDER_APPLE = 3
    PROVIDER_AMAZON = 4
    PROVIDER_CREDITCARD = 5

    PROVIDER_CHOICES = (
        (PROVIDER_NONE, 'None'),
        (PROVIDER_VIRTUALCURRENCY, 'Virtual Currency'),
        (PROVIDER_GOOGLEPLAY, 'Google Play'),
        (PROVIDER_APPLE, 'Apple'),
        (PROVIDER_AMAZON, 'Amazon'),
        (PROVIDER_CREDITCARD, 'Credit Card'),
    )

    OrderId = models.CharField(max_length=36, unique=True, default=getUUID )
    TransactionId = models.CharField(max_length=128)
    TransactionStatus = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_INIT)
    PaymentProvider = models.IntegerField(choices=PROVIDER_CHOICES, default=PROVIDER_NONE)
    Currency = models.ForeignKey(CurrencyType)
    PurchaseDate = models.DateTimeField(default=timezone.now)
    Account = models.ForeignKey(UserAccount)
    Annotation = models.TextField(blank=True)

    def getItems(self):
        return [ item.Item for item in UserItems.objects.filter(Purchase = self.pk) ]
    
    def __str__(self):
        return self.OrderId
    
class UserItems(models.Model):
    Item = models.ForeignKey(CatalogItem)
    Purchase = models.ForeignKey(Purchase, null=True, blank=True)
    Account = models.ForeignKey(UserAccount)
    RemainingUses = models.IntegerField(default=0)
    Expiration = models.DateTimeField(null=True, blank=True)
    Annotation = models.TextField(blank=True)
    BundleParent = models.ForeignKey(CatalogItem, related_name='bundle_parent', null=True, blank=True)
    
    def isConsumeable(self):
        return self.Item.isConsumeable()
    
    def consume(self, count):
        pass
    
    def getUserRepresentation(self):
        itemProps = self.Item.getUserRepresentation()
        
        if self.RemainingUses > 0:
            itemProps['RemainingUses'] = self.RemainingUses
        
        #if self.Purchase:
        #    itemProps['PurchaseDate'] = self.Purchase.PurchaseDate

        #if self.Expiration:
        #    itemProps['Expiration'] = self.Expiration
        
        if self.BundleParent:
            itemProps['BundleParent'] = self.BundleParent.ItemId
        
        return itemProps

    def __str__(self):
        return ' '.join([self.Item.ItemId, self.Account.DisplayName])

class TitleData(models.Model):
    Key = models.CharField(max_length=64)
    Data = models.TextField()

    def __str__(self):
        return self.Key

class NewsItem(models.Model):
    Title = models.CharField(max_length=128)
    Body = models.TextField()
    Timestamp = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.Title + ' (' + str(self.Timestamp) + ')'
