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

from django.contrib import admin
from openplaykit.models import *
from django import forms
from django.conf.urls import *
from django.shortcuts import render
from django.core import urlresolvers

class UserDataInline(admin.TabularInline):
	model = UserData
	extra = 1

class UserCurrencyInline(admin.TabularInline):
	model = UserCurrency
	extra = 0

class UserItemsInline(admin.TabularInline):
	raw_id_fields = ('Purchase',)
	model = UserItems
	extra = 0

class AndroidDeviceInline(admin.TabularInline):
	model = AndroidDevice
	extra = 0

class IOSDeviceInline(admin.TabularInline):
	model = IOSDevice
	extra = 0

class PurchaseInline(admin.TabularInline):
	model = Purchase
	extra = 0

class ProductForm(forms.Form):
	product = forms.CharField(max_length=100)

class UserAccountAdmin(admin.ModelAdmin):
	fieldsets = (
		('User', {'fields': ( 'UUID', 'DisplayName', 'Active' ) } ),
		('Details', {'classes': ('collapse',), 'fields': ( 'SessionTicket', 'Origination', 'Created', 'FirstLogin', 'LastLogin', 'Annotations', 'LegacyProduct' ) } ),
	)
	inlines = [ UserCurrencyInline, UserItemsInline, UserDataInline, AndroidDeviceInline, IOSDeviceInline, PurchaseInline ]
	readonly_fields = ['LegacyProduct']
	
class ManagedUserAccountAdmin(admin.ModelAdmin):
	raw_id_fields = ('Account',)
	search_fields = ('=Username',)
	readonly_fields = ['Link']
	
	# Create link to main account
	def Link(self, obj):
		return '<a style="padding: 5px; -webkit-appearance: button; -moz-appearance: button; appearance: button; text-decoration: none; color: initial;" href="../../useraccount/'+str(obj.Account.pk)+'/">Goto Account</a>'
	Link.allow_tags = True

class CatalogItemForm(forms.ModelForm):	
	class Meta:
		model = CatalogItem


class CatalogAdmin(admin.ModelAdmin):
	readonly_fields = ['Created', 'Items', 'Duplicate']

	# Show list of catalog items
	def Items(self, obj):
		items = CatalogItem.objects.filter(Catalog=obj.pk)
		items = sorted(items, key=lambda x : x.ItemId )
		
		result = """<div class="results"><table id="result_list" width="100%">
<thead><tr>
<th scope="col"><div class="text"><span>ItemId</span></div><div class="clear"></div></th>
<th scope="col"><div class="text"><span>Display Name</span></div><div class="clear"></div></th>
<th scope="col"><div class="text"><span>Description</span></div><div class="clear"></div></th>
<th scope="col"><div class="text"><span>Price</span></div><div class="clear"></div></th>
<th scope="col"><div class="text"><span>Bundle VC</span></div><div class="clear"></div></th>
<th scope="col"><div class="text"><span>Bundle Items</span></div><div class="clear"></div></th>
</tr></thead><tbody>"""

		i = 1
		for item in items:
			result = result + '<tr class="row'+str(i)+'"><th><a href="/admin/openplaykit/catalogitem/'+str(item.pk)+'/">'+item.ItemId+'</a></th>'
			result = result + '<th>'+item.DisplayName+'</th><th>'+item.Description+'</th>'
			result = result + '<th>'+", ".join(str(i) for i in item.getItemPrices())+'</th>'
			result = result + '<th>'+", ".join(str(i) for i in item.getCurrencyBundles())+'</th>'
			result = result + '<th>'+", ".join(str(i) for i in item.getItemBundles())+'</th>'
			result = result + '</tr>'
			i = i ^ 1;

		result = result + '<tr class="add-row"><td colspan="6"><a href="/admin/openplaykit/catalogitem/add?Catalog=' + str(obj.pk) + '"><img src="/media/admin/img/icon_addlink.gif"/> Add another Item</a></td></tr>'
		
		return result + "</tbody></table></div>"
	Items.allow_tags = True
	
	# Duplicate button
	def Duplicate(self, obj):
		return '<a style="padding: 5px; -webkit-appearance: button; -moz-appearance: button; appearance: button; text-decoration: none; color: initial;" href="javascript: if( confirm(\'Duplicate catalog?\') ) { location.href += \'DuplicateCatalog\'}">Make Copy</a>'
	Duplicate.allow_tags = True
	
	def get_urls(self):
		urls = super(CatalogAdmin, self).get_urls()
		my_urls = patterns('',
			(r'^([0-9]+)/DuplicateCatalog$', self.admin_site.admin_view(self.DuplicateCatalog))
		)
		return my_urls + urls

	def DuplicateCatalog(self, request, catalogId):
		from django.http import HttpResponseRedirect
		catalog = Catalog.objects.get(pk=catalogId)
		catalogitems = CatalogItem.objects.filter(Catalog=catalog)
		
		# Get unique name
		i = 0
		while True:
			i = i + 1
			name = catalog.Name.replace(' Copy ', '')
			name = catalog.Name + ' Copy ' + str(i)
			try:
				Catalog.objects.get(Name=name)
			except exceptions.ObjectDoesNotExist:
				break
			continue

		catalog.pk = None  
		catalog.Name = name
		catalog.save()
		
		itemLookup = {}
		
		# Put bundled items last
		catalogitems = sorted(catalogitems, key=lambda item : len( item.getItemBundles() ) )

		# Duplicate child objects		
		for item in catalogitems:

			itemPrice = item.getItemPrices()
			attributes = item.getAttributes()
			itemPrices = item.getItemPrices()
			currencyBundles = item.getCurrencyBundles()
			itemBundles = item.getItemBundles()
			
			oldPk = item.pk
			
			item.pk = None
			item.Catalog = catalog
			item.save()
			itemLookup[oldPk] = item.pk
			
			for price in itemPrice:
				price.Item = item
				price.pk = None
				price.save()
			
			for attrib in attributes:
				attrib.Item = item
				attrib.pk = None
				attrib.save()
				
			for price in itemPrices:
				price.Item = item
				price.pk = None
				price.save()
			
			for currency in currencyBundles:
				currency.Item = item
				currency.pk = None
				currency.save()
				
			for itemBund in itemBundles:
				itemBund.Item = item
				itemBund.BundledItem_id = itemLookup[itemBund.BundledItem_id]
				itemBund.pk = None
				itemBund.save()
			
		return HttpResponseRedirect('../'+str(catalog.pk) )

"""
CataLog Item
"""
class ItemPriceInline(admin.TabularInline):
	model = ItemPrice
	extra = 1

class BundleCurrencyInline(admin.TabularInline):
	model = BundleCurrency
	extra = 1

class BundleItemInline(admin.TabularInline):
	model = BundleItem
	extra = 1
	fk_name = "Item"
	
class ItemAttributeInline(admin.TabularInline):
	model = ItemAttribute
	extra = 1

class CatalogItemAdmin(admin.ModelAdmin):
	fieldsets = (
		('Item', {'fields': ( 'ItemId', 'DisplayName', 'Description', 'ItemClass', 'Catalog' ) } ),
		('Usage Parameters', {'fields': ( 'UsageCount', 'UsagePeriod', 'ConsumeOnPurchase' ), 'description': 'Note: Any item with a usage count is consumable. Usage period must accompany a usage count.' } ),
		('Options', {'classes': ('collapse',), 'fields': ( 'IsStackable', 'IsTradeable', 'ItemImageUrl') } ),
		('Container', {'classes': ('collapse',), 'fields': ( 'IsContainer', 'UnlockKey' ), 'description': 'Note: If container type selected item must be have a usage count.' } ),
	)
	inlines = [ ItemPriceInline, BundleCurrencyInline, BundleItemInline, ItemAttributeInline ]


admin.site.register(UserAccount, UserAccountAdmin)
admin.site.register(ManagedUserAccount, ManagedUserAccountAdmin)
admin.site.register(CurrencyType)
admin.site.register(Catalog, CatalogAdmin)
admin.site.register(CatalogItem, CatalogItemAdmin)
admin.site.register(NewsItem)
admin.site.register(TitleData)

