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

import datetime
import json

from django.http import HttpResponseBadRequest, HttpResponse
from django.core import exceptions

from openplaykit.apimodel import ErrorCodes
from openplaykit.models import *
from django.db.models.base import Model

from django.core.serializers.json import DjangoJSONEncoder

class JsonResponse(HttpResponse):
	def __init__(self, data, encoder=DjangoJSONEncoder, safe=True, **kwargs):
		if safe and not isinstance(data, dict):
			raise TypeError('In order to allow non-dict objects to be serialized set the safe parameter to False')
		kwargs.setdefault('content_type', 'application/json')
		data = json.dumps(data, cls=encoder)
		super(JsonResponse, self).__init__(content=data, **kwargs)

def SuccessResponse( data={} ):
	success = {'code': 200, 'status': 'OK'}
	if data != None:
		success['data'] = data
	return JsonResponse(success)

def ErrorHttpResponse(request, httpcode, httpstatus, error, errorCode, errorMessage, errorDetails={}):
	# If client asks don't return the RFC HTTP code instead fake a 200 code
	if httpcode != 200 and request.META.get('HTTP_X_HTTPERRORASSUCCESS'):
		httpcode = 200
	return JsonResponse({'code': httpcode, 'status': httpstatus, 'errorCode': errorCode, 'errorMessage': errorMessage, 'errorDetails': errorDetails }, status=httpcode)

def isNotJSONRequest(request):
	return request.method != 'POST' or request.META.get('CONTENT_TYPE') != 'application/json'

def getAuthenticatedUser(request):
	Authorization = request.META.get('HTTP_X_AUTHORIZATION')

	if Authorization == None:
		raise Exception('Authorization token missing')

	try:
		UserAccount.objects.get(SessionTicket=Authorization)
	except exceptions.ObjectDoesNotExist:
		raise Exception('No authorization token')

	return UserAccount.objects.get(SessionTicket=Authorization)

def GetJsonRequest(body):
	try:
		jsonrequest = json.loads(body)
	except:
		jsonrequest = json.loads(body, encoding="ISO-8859-1")
		
	if type(jsonrequest) is not dict:
		raise TypeError('Invalid request type')
	return jsonrequest

def LoginWithPlayFab(request):

	if isNotJSONRequest(request):
		return HttpResponseBadRequest()

	# Request: {"TitleId": "1", "Username": "theuser", "Password": "thepassword" }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidRequest, str(err) )

	Username = jsonrequest.get('Username')
	
	if ( Username == None ):
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing Username' )
	
	try:
		managedUserAccount = ManagedUserAccount.objects.get(Username=Username)
	except exceptions.ObjectDoesNotExist:
		return ErrorHttpResponse(request, 401, 'Unauthorized', 'AccountNotFound', ErrorCodes.AccountNotFound, 'Account Not Found' )
	except exceptions.MultipleObjectsReturned:
		return ErrorHttpResponse(request, 400, 'Unauthorized', 'DuplicateUsername', ErrorCodes.DuplicateUsername, 'Duplicate Username' )
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, 'Unknown Error' )
	
	Password = jsonrequest.get('Password', '')
	
	if ( len( Password) <= 0 ):
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidRequest, 'Invalid Password' )
	
	if ( managedUserAccount.checkPassword(Password) ):
		
		userAccount = managedUserAccount.Account
		try:
			userAccount.loginRefresh()
			userAccount.save()
		except Exception as err:
			return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, 'Unknown Error' )

		return SuccessResponse({'SessionTicket': userAccount.SessionTicket, 'NewlyCreated': False, 'PlayFabId': userAccount.UUID })	
	else:
		return ErrorHttpResponse(request, 401, 'Unauthorized', 'InvalidUsernameOrPassword', ErrorCodes.InvalidUsernameOrPassword, 'Invalid Username Or Password' )

def RegisterPlayFabUser(request):

	from django.core.exceptions import ValidationError
	from django.core.validators import validate_email

	# Request: {"TitleId":"1","Username":"test","Email":"nathan@bubblezap.com","Password":"test","Origination":"Android"}
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()

	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )

	# Validate password
	Password = jsonrequest.get('Password')
	
	if Password == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing Password' )
	
	if len(Password) < 6 or len(Password) > 30:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Invalid input parameters', {"Password":["Password must be between 6 and 30 characters."]} )

	# Note: The default value should be True
	requireBothUsernameAndEmail = jsonrequest.get('requireBothUsernameAndEmail', False) == True

	# Validate Username
	username = jsonrequest.get('Username')
	
	if username == None and requireBothUsernameAndEmail:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing Username' )
	
	# Validate Email
	Email = jsonrequest.get('Email')
	
	if Email == None and requireBothUsernameAndEmail:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing Email' )
	
	if Email != None:
		try:
			validate_email(Email)
		except ValidationError:
			return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidEmailAddress', ErrorCodes.InvalidEmailAddress, 'Invalid email address', {"Email":["Email is not valid."]} )

	# Check if username is already used
	if username != None:
		try:
			ManagedUserAccount.objects.get(Username=username)
			return ErrorHttpResponse(request, 400, 'BadRequest', 'UsernameNotAvailable', ErrorCodes.UsernameNotAvailable, 'Username is not available', {"Username":["User name already exists."]} )
		except exceptions.ObjectDoesNotExist:
			pass
		except Exception as err:
			return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, 'Unknown Error' )

	displayName = jsonrequest.get('DisplayName', '')
	Origination = jsonrequest.get('Origination', 'Unknown')

	# Create user accounts
	userAccount = UserAccount.objects.create(Origination=Origination, DisplayName=displayName)

	managedUserAccount = ManagedUserAccount.objects.create(Account=userAccount)
	if username != None:
		managedUserAccount.Username = username
	if Email != None:
		managedUserAccount.Email = Email
	
	managedUserAccount.setPassword( Password )
	managedUserAccount.save()

	# {"code":200,"status":"OK","jsonrequest":{"PlayFabId":"1EBAC35E14A7B102","SessionTicket":"1EBAC35E14A7B102--4A4-B79-8D1CA1F0B26F028-2391AF3CBA512CE3.90FF8F2435625CF9","Username":"rival667"}}
	return SuccessResponse({"PlayFabId": userAccount.UUID, 'SessionTicket': userAccount.SessionTicket, 'Username': username } )

def LoginWithAndroidDeviceID(request):
	
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
	
	# Request: { "TitleId": "1", "AndroidDeviceId": "59872d98fa632brn8hg3770", "OS": "4.4", "AndroidDevice": "Samsung Galaxy S3", "CreateAccount": false }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )

	androidDeviceId = jsonrequest.get('AndroidDeviceId')
	if androidDeviceId == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing AndroidDeviceId' )
	
	deviceName = jsonrequest.get('AndroidDevice')
	if deviceName == None:
		deviceName = 'Unknown'
	
	os = jsonrequest.get('OS')
	if os == None:
		os = 'Unknown'

	createAccount = jsonrequest.get('CreateAccount');

	newlyCreated = False

	try:
		androidAccount = AndroidDevice.objects.get(AndroidDeviceId=androidDeviceId)
	except exceptions.ObjectDoesNotExist:
		newlyCreated = True
		try:
			userAccount = UserAccount.objects.create(Origination='Android', LastLogin=datetime.datetime.min, FirstLogin=datetime.datetime.min)
			androidAccount = AndroidDevice.objects.create(AndroidDeviceId=androidDeviceId, OS=os, DeviceName=deviceName, Account=userAccount)
		except Exception as err:
			return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, 'Unknown Error' )
		if createAccount == True:
			ManagedUserAccount.objects.create(Account=userAccount)
	except exceptions.MultipleObjectsReturned:
		return ErrorHttpResponse(request, 400, 'Error', 'LinkedAccountAlreadyClaimed', ErrorCodes.LinkedAccountAlreadyClaimed, 'Linked account already claimed' )
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, str(err) )
	
	androidAccount.Account.loginRefresh()
	androidAccount.Account.save()

	# { "SessionTicket": "4D2----8D11F4249A80000-7C64AB0A9F1D8D1A.CD803BF233CE76CC", "NewlyCreated": false }
	return SuccessResponse({'SessionTicket': androidAccount.Account.SessionTicket, 'NewlyCreated': newlyCreated, 'PlayFabId': androidAccount.Account.UUID })

def AddUsernamePassword(request):

	if isNotJSONRequest(request):
		return HttpResponseBadRequest()

	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )

	# Request: {"Username": "theuser", "Email": "me@here.com", "Password": "thepassword"}
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )

	# Validate Username
	username = jsonrequest.get('Username')
	
	if username == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing Username' )

	# Validate password
	Password = jsonrequest.get('Password')
	
	if Password == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing Password' )
	
	if len(Password) < 6 or len(Password) > 30:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Invalid input parameters', {"Password":["Password must be between 6 and 30 characters."]} )

	return SuccessResponse({"Username": username })


def UpdateEmailAddress(request):
	
	from django.core.exceptions import ValidationError
	from django.core.validators import validate_email
	
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()

	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )
	
	# Request: { "Email": "dev@null.com" }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )
	
	Email = jsonrequest.get('Email')
	
	if Email == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing Email' )

	try:
		validate_email(Email)
	except ValidationError:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidEmailAddress', ErrorCodes.InvalidEmailAddress, 'Invalid email address', {"Email":["Email is not valid."]} )

	try:
		managedUserAccount = ManagedUserAccount.objects.get(Account=userAccount)
	except exceptions.ObjectDoesNotExist:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Account not registered' )
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'UnknownError', ErrorCodes.UnknownError, str(err) )
	
	if managedUserAccount.Email == Email:
		return SuccessResponse({})
	
	if not ManagedUserAccount.isUniqueEmail():
		return ErrorHttpResponse(request, 400, 'BadRequest', 'EmailAddressNotAvailable', ErrorCodes.EmailAddressNotAvailable, 'Email address not available' )
	
	# Update email
	managedUserAccount.Email = Email
	try:
		managedUserAccount.save(update_fields=['Email'])
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, 'Unknown Error' )
	
	# Return Success
	return SuccessResponse({})

def UpdatePassword(request):
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()

	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )
	
	# Request: { "Email": "dev@null.com" }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )
	
	# Validate password
	Password = jsonrequest.get('Password')
	
	if Password == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing Password' )
	
	if len(Password) < 6 or len(Password) > 30:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Invalid input parameters', {"Password":["Password must be between 6 and 30 characters."]} )
	
	managedUserAccount = ManagedUserAccount.objects.get(Account=userAccount)
	managedUserAccount.setPassword( Password )
	managedUserAccount.save()
	
def UpdateUserTitleDisplayName(request):

	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
	
	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )
	
	# Request: { "DisplayName": "User Title Name" }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )
	
	DisplayName = jsonrequest.get('DisplayName')
	
	if DisplayName == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing DisplayName' )
	
	userAccount.DisplayName = DisplayName
	try:
		userAccount.save(update_fields=['DisplayName'])
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, 'Unknown Error' )
	
	# {"DisplayName":"username"}
	return SuccessResponse({"DisplayName":DisplayName})

def LoginWithFacebook(request):
	# { "TitleId": "1", "AccessToken": "FaceAccessTokenID", "CreateAccount": false }
	# { "SessionTicket": "4D2----8D11F4249A80000-7C64AB0A9F1D8D1A.CD803BF233CE76CC", "NewlyCreated": false }
	pass	

def LoginWithGameCenter(request):
	# { "TitleId": "1", "PlayerId": "pachycephalosaurus01", "CreateAccount": false }
	# { "SessionTicket": "4D2----8D11F4249A80000-7C64AB0A9F1D8D1A.CD803BF233CE76CC", "NewlyCreated": false }
	pass

def LoginWithGoogleAccount(request):
	# { "TitleId": "1", "AccessToken": "BInn23arRiCepodeRQ" }
	# { "SessionTicket": "4D2----8D11F4249A80000-7C64AB0A9F1D8D1A.CD803BF233CE76CC", "NewlyCreated": false }
	pass

def LoginWithIOSDeviceID(request):
	
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
	
	# Request: { "TitleId": "1", "DeviceId": "29848d9bh8900a0b003", "OS": "7.11", "DeviceModel": "Iphone 5s", "CreateAccount": false }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )

	DeviceId = jsonrequest.get('DeviceId')
	if DeviceId == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing DeviceId' )
	
	deviceModel = jsonrequest.get('DeviceModel')
	if deviceModel == None:
		deviceModel = 'Unknown'
	
	os = jsonrequest.get('OS')
	if os == None:
		os = 'Unknown'

	createAccount = jsonrequest.get('CreateAccount');

	newlyCreated = False

	try:
		iosAccount = IOSDevice.objects.get(IOSDeviceId=DeviceId)
	except exceptions.ObjectDoesNotExist:
		newlyCreated = True
		try:
			userAccount = UserAccount.objects.create(Origination='iOS', LastLogin=datetime.datetime.min, FirstLogin=datetime.datetime.min)
			iosAccount = IOSDevice.objects.create(IOSDeviceId=DeviceId, OS=os, DeviceModel=deviceModel, Account=userAccount)
		except Exception as err:
			return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, 'Unknown Error' )
		if createAccount == True:
			ManagedUserAccount.objects.create(Account=userAccount)
	except exceptions.MultipleObjectsReturned:
		return ErrorHttpResponse(request, 400, 'Error', 'LinkedAccountAlreadyClaimed', ErrorCodes.LinkedAccountAlreadyClaimed, 'Linked account already claimed' )
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, str(err) )
	
	iosAccount.Account.loginRefresh()
	iosAccount.Account.save()

	# { "SessionTicket": "4D2----8D11F4249A80000-7C64AB0A9F1D8D1A.CD803BF233CE76CC", "NewlyCreated": false }
	return SuccessResponse({'SessionTicket': iosAccount.Account.SessionTicket, 'NewlyCreated': newlyCreated, 'PlayFabId': iosAccount.Account.UUID })

def LoginWithSteam(request):
	# { "TitleId": "1", "SteamTicket": "steamTicketID", "CreateAccount": false }
	# { "SessionTicket": "4D2----8D11F4249A80000-7C64AB0A9F1D8D1A.CD803BF233CE76CC", "NewlyCreated": false }
	pass	

def SendAccountRecoveryEmail(request):
	
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()

	# { "Email": "Me@here.com", "TitleId": "1000" }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )
	
	pass

def GetAccountInfo(request):
	# { "PlayFabId": "10931252888739651331" }
	# { "AccountInfo": { "PlayFabId": "10931252888739651331", "Created": "2013-04-07T09:04:28Z", "Username": "accountname", "TitleInfo": { "Origination": "IOS", "Created": "2014-01-08T11:03:18Z", "LastLogin": "2014-04-07T09:04:28Z", "FirstLogin": "2014-01-08T11:03:18Z" }, "FacebookInfo": { "FacebookId": "23525445454" }, "SteamInfo": { "SteamCountry": "US", "SteamCurrency": "USD" }, "GameCenterInfo": { "GameCenterId": "someone" } } }
	pass

def GetPlayFabIDsFromFacebookIDs(request):
	# { "FacebookIDs": [ "857498576495", "759374651209" ] }
	# { "Data": [ { "FacebookId": "857498576495", "PlayFabId": "5a446c83645201" }, { "FacebookId": "759374651209", "PlayFabId": "6345cd25a6c7cc" } ] }
	pass

def GetUserCombinedInfo(request):
	# { "GetInventory": false, "UserDataKeys": [ "preferences", "progress" ], "GetReadOnlyData": false }
	# { "PlayFabId": "10931252888739651331", "AccountInfo": { "PlayFabId": "10931252888739651331", "Created": "2013-04-07T09:04:28Z", "Username": "accountname", "TitleInfo": { "Origination": "IOS", "Created": "2014-01-08T11:03:18Z", "LastLogin": "2014-04-07T09:04:28Z", "FirstLogin": "2014-01-08T11:03:18Z" }, "FacebookInfo": { "FacebookId": "23525445454" }, "SteamInfo": { "SteamCountry": "US", "SteamCurrency": "USD" }, "GameCenterInfo": { "GameCenterId": "someone" } }, "VirtualCurrency": { "GC": 15 }, "Data": { "preferences": { "Value": "alpha", "LastUpdated": "2014-08-20T12:30:45Z", "Permission": "Public" }, "progress": { "Value": "level_twenty", "LastUpdated": "2014-09-01T10:12:30Z", "Permission": "Private" } } }
	pass

def LinkAndroidDeviceID(request):
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
	
	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )

	# Request: {"AndroidDeviceId": "526f79204261747479", "OS": "5.0", "AndroidDevice": "Nexus 6" }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )

	androidDeviceId = jsonrequest.get('AndroidDeviceId')
	if androidDeviceId == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing AndroidDeviceId' )
	
	deviceName = jsonrequest.get('AndroidDevice')
	if deviceName == None:
		deviceName = 'Unknown'

	os = jsonrequest.get('OS')
	if os == None:
		os = 'Unknown'

	try:
		AndroidDevice.objects.get(AndroidDeviceId=androidDeviceId, Account=userAccount)
		return ErrorHttpResponse(request, 400, 'Error', 'AccountAlreadyLinked', ErrorCodes.AccountAlreadyLinked, 'Account already linked' )
	except exceptions.ObjectDoesNotExist:
		try:
			AndroidDevice.objects.create(AndroidDeviceId=androidDeviceId, OS=os, DeviceName=deviceName, Account=userAccount)
		except Exception as err:
			return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, str(err) )
		return SuccessResponse({})
	except exceptions.MultipleObjectsReturned:
		return ErrorHttpResponse(request, 400, 'Error', 'LinkedAccountAlreadyClaimed', ErrorCodes.LinkedAccountAlreadyClaimed, 'Linked account already claimed' )
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, str(err) )


def LinkFacebookAccount(request):
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
	
	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )
	
	# { "AccessToken": "FaceAccessTokenID", "ForceLink": false }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )

	accessToken = jsonrequest.get('AccessToken')
	if accessToken == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing accessToken' )

	forceLink = accessToken = jsonrequest.get('ForceLink', False)

	try:
		fbAccount, created = FaceBookAccount.objects.get_or_create(Account=userAccount)
		if created or forceLink:
			fbAccount.AccessToken = accessToken
			fbAccount.save()
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, str(err) )
	
	return SuccessResponse({})

def LinkGameCenterAccount(request):
	# { "GameCenterId": "2998h2998f0b000d0993" }
	pass

def LinkSteamAccount(request):
	# { "SteamTicket": "steamTicketID" }
	pass

def UnlinkFacebookAccount(request):
	pass

def UnlinkGameCenterAccount(request):
	pass

def UnlinkSteamAccount(request):
	pass

def GetFriendLeaderboard(request):
	pass

def GetLeaderboard(request):
	pass

def GetLeaderboardAroundCurrentUser(request):
	pass

def GetUserData(request):
	
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
	
	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )
	
	# Request: { "Keys": ["preferences","progress"] }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )

	Keys = jsonrequest.get('Keys')
	
	if Keys and type(Keys) == type([]):
		resultData = {}
		for k in Keys:
			try:
				userData = UserData.objects.get(Account=userAccount, Key=k)
				resultData[k] = {'Value': userData.Data, 'LastUpdate': userData.LastUpdated, 'Permission': 'Public' }
			except exceptions.ObjectDoesNotExist:
				pass
			except Exception as err:
				return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, str(err) )
	else:
		try:
			userData = UserData.objects.filter(Account=userAccount)
			resultData = { item.Key: {'Value': item.Data, 'LastUpdate': item.LastUpdated, 'Permission': 'Public' } for item in userData }
		except Exception as err:
			return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, str(err) )

	return SuccessResponse({'Data': resultData})

def GetUserReadOnlyData(request):
	pass

def GetUserStatistics(request):
	pass

def UpdateUserData(request):
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
	
	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )
	
	# Request: { "Data": { "Class": "Fighter", "Gender": "Female", "Icon": "Guard 3", "Theme": "Colorful" }, "Permission": "Public" }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )

	data = jsonrequest.get('Data')
	permission = jsonrequest.get('Permission')

	for key, value in data.items():
		try:
			try:
				userData, created = UserData.objects.get_or_create(Key=key, Account=userAccount)
			except exceptions.MultipleObjectsReturned:
				# Clear multiple records
				try:
					UserData.objects.filter(Key=key, Account=userAccount.id).delete()
					userData, created = UserData.objects.get_or_create(Key=key, Account=userAccount)
				except Exception as err:
					return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, 'Unknown Error' )
				
			userData.Data = value
			try:
				userData.save()
			except Exception as err:
				return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, 'Unknown Error' )

		except Exception as err:
			return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, str(err) )
	
	return SuccessResponse({})

def validateGoogleSignature(publicKey, signedData, signature):
	from Crypto.Hash import SHA
	from Crypto.PublicKey import RSA
	from Crypto.Signature import PKCS1_v1_5
	from base64 import b64decode

	def chunks(s, n):
		for start in range(0, len(s), n):
			yield s[start:start+n]
		
	def pem_format(key):
		return '\n'.join([ '-----BEGIN PUBLIC KEY-----', '\n'.join(chunks(key, 64)), '-----END PUBLIC KEY-----' ])
	
	key = RSA.importKey(pem_format(publicKey))
	verifier = PKCS1_v1_5.new(key)
	data = SHA.new(signedData)
	sig = b64decode(signature)
	return verifier.verify(data, sig)

def ValidateGooglePlayPurchase(request):
	
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()

	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )
	
	# Request: { "ReceiptJson": "{\"orderId\":\"12999763169054705758.13757940665876
	# 22\",\"packageName\":\"com.playfab.android.testbed\",\"productId\":\"com.play
	# fab.android.permatest.consumable\",\"purchaseTime\":1410891177231,\"purchaseS
	# tate\":0,\"purchaseToken\":\"eaflhokdkobkmomjadmoobgb.AO-
	# J1OwoLkW2cqvBcPEgk6SfGceQpOHALMUFmJYeawa-GuDFtl3oKct-
	# 5D28t_KvNscFiJOFiWXIS74vJBYg-CGFJgyrdbxalKEMPzXZrg5nLomCME-jIVFAUrzcPah-
	# _66KPImG5ftsMJKI9uzldqEF9OPcakUEmt-kWoXAsl_6-9HH0gBCwh4\"}", "Signature": "ks
	# 12w0hHHpuit4xW3Fyoa5XX6TkxZ2KpEnBsLfpHHpeakYs2JgVtlLdgyLp/05Zp8oHAuKZyIAJTd2R
	# IFXWMAUwDNUsI0JPBDMpr2oaL66Kuneg4VrGWJkJZTrvTyQoGpnTDdXfEME31iFKX6CrKHvWlAG9n
	# wWxYatd58l83eevQ8CIrJhka/bC5ynw3j18OmFG7AcxymO37a4HkM8QjytvAYDJeOnDU9mooY7afc
	# HIajtffdyAU9kzGWOqDByiU9IsRdkliwQoQYbuX/R5wQnMVZ+FGDDwO1mybx9B20rm7/WCBnWGy2N
	# LsSAFI77iX8tUy/QebfBQhrVnRORi7bw==" }

	# Parse request
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )

	signature = jsonrequest.get('Signature')
	if signature == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing Signature' )

	receiptJson = jsonrequest.get('ReceiptJson')
	if receiptJson == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing ReceiptJson' )
	
	# Parse receipt
	try:
		receipt = json.loads(receiptJson)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )
	
	transactionId = receipt.get('orderId')

	itemId = receipt.get('productId')
	if itemId == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing productId' )

	# Find the product
	try:
		itemList = CatalogItem.objects.filter(ItemId = itemId)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'ItemNotFound', ErrorCodes.ItemNotFound, 'Item not found' )
	
	if len(itemList) == 0:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'ItemNotFound', ErrorCodes.ItemNotFound, 'Item not found' )
	
	itemList = sorted(itemList, key=lambda x : x.Catalog.Created, reverse=True )
	item = itemList[0]
		
	# See if item can be purchased with Real Money (RM)
	itemPrice = item.getItemPrice('RM')
	if itemPrice == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'PurchaseDoesNotExist', ErrorCodes.PurchaseDoesNotExist, 'Purchase does not exist' )

	# Validate signature
	try:
		import settings
		publicKey = settings.GOOGLE_PUBLIC_KEY
	except (ImportError, AttributeError) as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'UnknownError', ErrorCodes.UnknownError, 'Server misconfiguration. ' + str(err) )

	try:
		if validateGoogleSignature(publicKey, receiptJson, signature):
			pass
		else:
			# Record the bad transaction
			try:
				purchase = Purchase.objects.create(TransactionStatus=Purchase.STATUS_FAILEDBYPROVIDER, PaymentProvider=Purchase.PROVIDER_GOOGLEPLAY, Currency=itemPrice.Currency, Account=userAccount, Annotation=receiptJson)
			except Exception as err:
				return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, str(err) )
			return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidReceipt', ErrorCodes.InvalidReceipt, 'Invalid Receipt' )
	except ImportError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'UnknownError', ErrorCodes.UnknownError, 'Server misconfiguration. ' + str(err) )
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidReceipt', ErrorCodes.InvalidReceipt, str(err) )
	
	# Check for receipt replay attack
	try: 
		purchases = Purchase.objects.filter(TransactionId=transactionId, PaymentProvider=Purchase.PROVIDER_GOOGLEPLAY).count()
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'UnknownError', ErrorCodes.UnknownError, str(err) )
	
	if purchases > 0:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'ReceiptAlreadyUsed', ErrorCodes.ReceiptAlreadyUsed, 'Receipt already used' )

	# Record the transaction
	try:
		purchase = Purchase.objects.create(TransactionId=transactionId, TransactionStatus=Purchase.STATUS_INIT, PaymentProvider=Purchase.PROVIDER_GOOGLEPLAY, Currency=itemPrice.Currency, Account=userAccount, Annotation=receiptJson)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, str(err) )
	
	# Give the player their items / currency
	try:
		item.assignToUser(userAccount, purchase)
	
		purchase.TransactionStatus = Purchase.STATUS_SUCCEEDED
		purchase.save()

	except Exception as err:
		return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, str(err) )

	return SuccessResponse({})

def parseAppleDataFormat( data ):
	# Remove last semi-colon
	lastSemiColon = data.rfind(';')
	if lastSemiColon > 0:
		data[lastSemiColon] = data[:lastSemiColon] + data[lastSemiColon+1:]
	data = data.replace(';', ',')
	data = data.replace('" = "', '": "')

	return json.loads(data)

def validateIOSSignature(signedData, signature):
	from Crypto.Hash import SHA
	from Crypto.PublicKey import RSA
	from Crypto.Signature import PKCS1_v1_5
	from base64 import b64decode

	appleCA = ''
	key = RSA.importKey(appleCA)
	verifier = PKCS1_v1_5.new(key)
	data = SHA.new(signedData)
	sig = b64decode(signature)
	return verifier.verify(data, sig)

def ValidateIOSReceipt(request):
	from base64 import b64decode
	
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()

	# Request: { "ReceiptData": "...", "CurrencyCode": "GBP", "PurchasePrice": 199 } 

	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )

	# Parse request
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )

	receiptDataEncoded = jsonrequest.get('ReceiptData')
	if receiptDataEncoded == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing ReceiptData' )
	
	currencyCode = jsonrequest.get('CurrencyCode')
	if currencyCode == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing CurrencyCode' )
	
	purchasePrice = jsonrequest.get('PurchasePrice')
	if purchasePrice == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing PurchasePrice' )

	try:
		receiptDataRaw = b64decode(receiptDataEncoded)
		receiptProperties = parseAppleDataFormat( receiptDataRaw )
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Invalid ReceiptData' )

	purchaseInfoEncoded = receiptProperties.get('purchase-info')
	if purchaseInfoEncoded == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Invalid ReceiptData' )

	try:
		purchaseInfoRaw = b64decode(purchaseInfoEncoded)
		purchaseInfo = parseAppleDataFormat( purchaseInfoRaw )		
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Invalid ReceiptData' )
	
	appleProductId = purchaseInfo.get('product-id')
	if appleProductId == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Invalid ReceiptData' )
	
	# TODO ???
	itemId = appleProductId

	# Find the product
	try:
		itemList = CatalogItem.objects.filter(ItemId = itemId)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'ItemNotFound', ErrorCodes.ItemNotFound, 'Item not found' )
	
	if len(itemList) == 0:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'ItemNotFound', ErrorCodes.ItemNotFound, 'Item not found' )
	
	itemList = sorted(itemList, key=lambda x : x.Catalog.Created, reverse=True )
	item = itemList[0]
		
	# See if item can be purchased with Real Money (RM)
	itemPrice = item.getItemPrice('RM')
	if itemPrice == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'PurchaseDoesNotExist', ErrorCodes.PurchaseDoesNotExist, 'Purchase does not exist' )

	transactionId = purchaseInfo.get('transaction-id')
	if transactionId == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Invalid ReceiptData' )
	
	# Validate signature
	signature = receiptProperties.get('signature')
	if signature == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Invalid ReceiptData' )
	
	if not validateIOSSignature(receiptDataRaw, signature):
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidReceipt', ErrorCodes.InvalidReceipt, 'Invalid Receipt' )

	# Check for receipt replay attack
	try: 
		purchases = Purchase.objects.filter(TransactionId=transactionId, PaymentProvider=Purchase.PROVIDER_APPLE).count()
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'UnknownError', ErrorCodes.UnknownError, str(err) )
	
	if purchases > 0:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'ReceiptAlreadyUsed', ErrorCodes.ReceiptAlreadyUsed, 'Receipt already used' )

	# Record the transaction
	try:
		purchase = Purchase.objects.create(TransactionId=transactionId, TransactionStatus=Purchase.STATUS_INIT, PaymentProvider=Purchase.PROVIDER_APPLE, Currency=itemPrice.Currency, Account=userAccount, Annotation=purchaseInfoRaw)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, str(err) )
	
	# Give the player their items / currency
	try:
		item.assignToUser(userAccount, purchase)
	
		purchase.TransactionStatus = Purchase.STATUS_SUCCEEDED
		purchase.save()

	except Exception as err:
		return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, str(err) )

	return SuccessResponse({})
	

def RegisterForIOSPushNotification(request):
	pass

def UpdateUserStatistics(request):
	pass

def GetCatalogItems(request):

	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
	
	# Check authorization
	try:
		getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )

	# Parse request
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )

	catalogVersion = jsonrequest.get('CatalogVersion')
	if catalogVersion == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing CatalogVersion' )
	
	try:
		catalog = Catalog.objects.get(Name=catalogVersion)
	except exceptions.ObjectDoesNotExist:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Could not find Catalog' )
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, str(err) )

	try:
		catalogItems = [ item.getCatalogRepresentation() for item in CatalogItem.objects.filter(Catalog=catalog) ]
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'Error', 'UnknownError', ErrorCodes.UnknownError, str(err) )


	return SuccessResponse({'Catalog': catalogItems })

def GetStoreItems(request):
	pass

def GetTitleData(request):
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
	
	# Check authorization
	try:
		getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )
	
	# Request: { "Keys": [ "color", "propertyA" ] }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )

	keys = jsonrequest.get('Keys')
	
	if keys and type(keys) == type([]):
		try:
			elements = TitleData.objects.filter(key__in=keys)
		except Exception, err:
			return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )
	else :
		elements = TitleData.objects.all()

	return SuccessResponse( {'Data': { e.Key: e.Data for e in elements } } )

def GetTitleNews(request):
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
	
	# Check authorization
	try:
		getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )
	
	# Request: { "Count": 25 }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )

	count = jsonrequest.get('Count', 10)

	news = []
	for item in NewsItem.objects.all():
		news.append( { 'Timestamp': item.Timestamp, 'Title': item.Title, 'Body': item.Body } )

	news = news[0:count]

	return SuccessResponse( {'News': news } )

def ConsumeItem(request):
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
	
	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )
	
	# Request: { "ItemInstanceId": "94585729", "ConsumeCount": 1 }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )

	itemInstanceId = jsonrequest.get('ItemInstanceId')
	itemId = jsonrequest.get('ItemId')

	consumeCount = jsonrequest.get('ConsumeCount')
	if consumeCount == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing ConsumeCount' )

	# Look up item by id
	if itemId != None:
		try:
			userItems = UserItems.objects.get(Account=userAccount)
		except exceptions.ObjectDoesNotExist:
			return ErrorHttpResponse(request, 400, 'BadRequest', 'ItemNotFound', ErrorCodes.ItemNotFound, 'Item not found' )

		for item in userItems:
			if item.Item.ItemId == itemId:
				userItem = item
				break	

		if userItem == None:
			return ErrorHttpResponse(request, 400, 'BadRequest', 'ItemNotFound', ErrorCodes.ItemNotFound, 'Item not found' )

	# Find item by InstanceId
	elif itemId != None:
		try:
			userItem = UserItems.objects.get(ItemId=itemId, Account=userAccount)
		except exceptions.ObjectDoesNotExist:
			return ErrorHttpResponse(request, 400, 'BadRequest', 'ItemNotFound', ErrorCodes.ItemNotFound, 'Item not found' )
	else:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing ItemInstanceId' )

	if userItem.RemainingUses >= consumeCount:
		# Consume
		userItem.consume(consumeCount)
		
		userItem.RemainingUses = userItem.RemainingUses - consumeCount

		if ( userItem.RemainingUses <= 0)
			userItem.RemainingUses = 0
			userItem.delete()
		else:
			userItem.save()
		
	else:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NoRemainingUses', ErrorCodes.NoRemainingUses, 'No remaining uses' )

	return SuccessResponse( {'ItemInstanceId': userItem.itemInstanceId, 'RemainingUses':  userItem.RemainingUses } )

def RedeemCoupon(request):
	pass

def AddUserVirtualCurrency(request, subtract=False):
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
	
	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )
	
	# Request: { "VirtualCurrency": "GC", "Amount": 100 }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )
	
	virtualCurrency = jsonrequest.get('VirtualCurrency')
	if virtualCurrency == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing VirtualCurrency' )
	
	amount = jsonrequest.get('Amount')
	if amount == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing Amount' )
	try:
		amount = int(amount)
		if amount < 1 or amount > 1000000:
			return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Invalid Amount' )
	except ValueError:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Invalid Amount' )

	try:
		userCurrency = userAccount.getCurrencyByCode(virtualCurrency)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'UnknownError', ErrorCodes.UnknownError, str(err) )

	# Enforce transaction limits
	if userCurrency.Currency.DirectTransactionLimit != 0 and amount > userCurrency.Currency.DirectTransactionLimit and subtract == False:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.APINotEnabledForGameClientAccess, 'Currency cannot be changed' )

	# Enforce remote currency changes
	if userCurrency.Currency.RemotelyMutable != True:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.APINotEnabledForGameClientAccess, 'Currency cannot be changed' )

	if subtract == True:
		balanceChange = -amount
	else:
		balanceChange = amount

	userCurrency.Amount = userCurrency.Amount + balanceChange
	
	if userCurrency.Amount < 0:
		userCurrency.Amount = 0

	try:
		userCurrency.save()
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'UnknownError', ErrorCodes.UnknownError, str(err) )

	return SuccessResponse( {'PlayFabId': userAccount.UUID, 'VirtualCurrency': virtualCurrency, 'BalanceChange': balanceChange, 'Balance': userCurrency.Amount } )

def SubtractUserVirtualCurrency(request):
	return AddUserVirtualCurrency(request, True)

def UnlockContainerItem(request):
	pass

def StartPurchase(request):
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
	
	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )
	
	# Request: { "CatalogVersion": "0", "StoreId": "BonusStore", "Items": [ { "ItemId": "something", "Quantity": 1, "Annotation": "totally buying something" } ] }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )

	# Response: { "code": 200, "status": "OK", "data": { "OrderId": "8853591446005860822", "Contents": [ { "ItemId": "shield_level_5", "ItemClass": "shields", "DisplayName": "Level 5 Shield", "VirtualCurrencyPrices": { "RM": 199, "GV": 25 }, "RealCurrencyPrices": { "GBP": 149, "EUR": 169 } } ], "PaymentOptions": [ { "Currency": "RM", "ProviderName": "Amazon", "Price": 199, "StoreCredit": 0 }, { "Currency": "GV", "ProviderName": "TitleA90A", "Price": 25, "StoreCredit": 0 } ], "VirtualCurrencyBalances": { "GV": 25 } } }
	pass

def PayForPurchase(request):
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
	
	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )
	
	# Request: { "OrderId": "8853591446005860822", "ProviderName": "PayPal", "Currency": "RM" }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )


	# Response: { "code": 200, "status": "OK", "data": { "OrderId": "8853591446005860822", "Status": 1, "PurchaseCurrency": "RM", "PurchasePrice": 199, "CreditApplied": 0 } }

def ConfirmPurchase(request):
	
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
	
	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )
	
	# Request: { "OrderId": "8853591446005860822" }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )

	# Response: { "code": 200, "status": "OK", "data": { "OrderId": "8853591446005860822", "PurchaseDate": "2014-04-07T09:04:28Z", "Items": [ { "ItemInstanceId": "40895075594", "ItemId": "shield_level_5", "CatalogVersion": "5", "DisplayName": "Level 5 Shield", "UnitCurrency": "GV", "UnitPrice": 25 } ] } }

	pass

def PurchaseItem(request):

	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
		
	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )

	# Request: { "ItemId": "shield_level_5", "VirtualCurrency": "GV", "Price": 25, CatalogVersion: 1 }
	try:
		jsonrequest = GetJsonRequest(request.body)
	except TypeError as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, str(err) )

	itemId = jsonrequest.get('ItemId')
	if itemId == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing ItemId' )

	virtualCurrency = jsonrequest.get('VirtualCurrency')
	if itemId == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing VirtualCurrency' )

	price = jsonrequest.get('Price')
	if itemId == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidParams', ErrorCodes.InvalidParams, 'Missing Price' )
	
	catalogVersion = jsonrequest.get('CatalogVersion')

	if catalogVersion == None:
		try:
			itemList = CatalogItem.objects.filter(ItemId = itemId)
		except Exception as err:
			return ErrorHttpResponse(request, 400, 'BadRequest', 'UnknownError', ErrorCodes.UnknownError, str(err) )
		
		if len(itemList) == 0:
			return ErrorHttpResponse(request, 400, 'BadRequest', 'ItemNotFound', ErrorCodes.ItemNotFound, 'Item not found' )

		# Grab the most recent
		itemList = sorted(itemList, key=lambda x : x.Catalog.Created, reverse=True )
		item = itemList[0]
	
	else:
		try:
			catalog = Catalog.objects.get(Name=catalogVersion)
			item = CatalogItem.objects.get(ItemId = itemId, Catalog=catalog)
		except exceptions.ObjectDoesNotExist:
			return ErrorHttpResponse(request, 400, 'BadRequest', 'ItemNotFound', ErrorCodes.ItemNotFound, 'Item not found' )
		except Exception as err:
			return ErrorHttpResponse(request, 400, 'BadRequest', 'UnknownError', ErrorCodes.UnknownError, str(err) )

	# Real money not allowed
	if virtualCurrency == 'RM':
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidVirtualCurrency', ErrorCodes.InvalidVirtualCurrency, 'Invalid Virtual Currency' )
	
	# See if item can be purchased with this VC
	try:
		itemPrice = item.getItemPrice(virtualCurrency)
	except Exception, err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'UnknownError', ErrorCodes.UnknownError, str(err) )
		
	if itemPrice == None:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InvalidVirtualCurrency', ErrorCodes.InvalidVirtualCurrency, 'Invalid Virtual Currency' )

	if price != itemPrice.Price:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'WrongPrice', ErrorCodes.WrongPrice, 'Wrong Price' )

	try:
		userCurrency = userAccount.getCurrencyByCode(virtualCurrency)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'UnknownError', ErrorCodes.UnknownError, str(err) )

	if userCurrency.canBuy(itemPrice.Price):
		
		# Record the purchase
		purchase = Purchase.objects.create(TransactionId=getUUID(), TransactionStatus=Purchase.STATUS_SUCCEEDED, PaymentProvider=Purchase.PROVIDER_VIRTUALCURRENCY, Currency=itemPrice.Currency, Account=userAccount)
		
		# Debit the cost of the item
		userCurrency.debit(itemPrice.Price)

		# Give the player their items / currency
		newItems = item.assignToUser(userAccount, purchase)

		# Response: { "code": 200, "status": "OK", "data": { "Items": [ { "ItemId": "shield_level_5", "CatalogVersion": "5", "DisplayName": "Level 5 Shield", "UnitCurrency": "GV", "UnitPrice": 25 } ] } }
		return SuccessResponse({'Items': newItems})
		
	else:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'InsufficientFunds', ErrorCodes.InsufficientFunds, 'Insufficient Funds' )

def GetUserInventory(request):

	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
	
	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )

	data = {}

	# Get all active inventory items
	try:
		userItems = userAccount.getUserItems()
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'UnknownError', ErrorCodes.UnknownError, str(err) )

	itemResults = []
	for item in userItems:
		itemResults.append( item.getUserRepresentation() )
	
	data['Inventory'] = itemResults

	# Get virtual currency
	virtualCurrency = {}

	try:
		allCurrency = CurrencyType.objects.all().exclude(CurrencyCode='RM')
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'UnknownError', ErrorCodes.UnknownError, str(err) )

	for currency in allCurrency:
		try:
			userCurrency = userAccount.getCurrency(currency)
		except Exception, err:
			return ErrorHttpResponse(request, 400, 'BadRequest', 'UnknownError', ErrorCodes.UnknownError, str(err) )
		
		virtualCurrency[currency.CurrencyCode] = userCurrency.Amount
		
	data['VirtualCurrency'] = virtualCurrency
	
	#data['VirtualCurrencyRechargeTimes'] = {}
	
	return SuccessResponse(data)

def AddFriend(request):
	pass

def GetFriendsList(request):
	pass

def RemoveFriend(request):
	pass

def SetFriendTags(request):
	pass

def GetCurrentGames(request):
	pass

def GetGameServerRegions(request):
	pass

def Matchmake(request):
	pass

def StartGame(request):
	pass

def AndroidDevicePushNotificationRegistration(request):
	pass

def LogEvent(request):
	pass

def AddSharedGroupMembers(request):
	pass

def CreateSharedGroup(request):
	pass

def GetSharedGroupData(request):
	pass

def RemoveSharedGroupMembers(request):
	pass

def UpdateSharedGroupData(request):
	pass

def GetLogicServerUrl(request):
	pass

def ResetUser(request):
	if isNotJSONRequest(request):
		return HttpResponseBadRequest()
	
	# Check authorization
	try:
		userAccount = getAuthenticatedUser(request)
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'NotAuthenticated', ErrorCodes.NotAuthenticated, str(err) )

	try:
		userAccount.SessionTicket = 'deleted'
		userAccount.Active = False
		userAccount.save()

		try:
			managedUserAccount = ManagedUserAccount.objects.get(Account=userAccount)
			managedUserAccount.delete()
		except exceptions.ObjectDoesNotExist:
			pass
	
		try:
			AndroidDevice.objects.filter(Account=userAccount).delete()
		except exceptions.ObjectDoesNotExist:
			pass

		try:
			IOSDevice.objects.filter(Account=userAccount).delete()
		except exceptions.ObjectDoesNotExist:
			pass
		
	except Exception as err:
		return ErrorHttpResponse(request, 400, 'BadRequest', 'UnknownError', ErrorCodes.UnknownError, str(err) )

	return SuccessResponse({})
