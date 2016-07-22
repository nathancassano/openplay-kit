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

class ErrorCodes:
    Unknown = 1
    Success = 0
    InvalidParams = 1000
    AccountNotFound = 1001
    AccountBanned = 1002
    InvalidUsernameOrPassword = 1003
    InvalidTitleId = 1004
    InvalidEmailAddress = 1005
    EmailAddressNotAvailable = 1006
    InvalidUsername = 1007
    InvalidPassword = 1008
    UsernameNotAvailable = 1009
    InvalidSteamTicket = 1010
    AccountAlreadyLinked = 1011
    LinkedAccountAlreadyClaimed = 1012
    InvalidFacebookToken = 1013
    AccountNotLinked = 1014
    FailedByPaymentProvider = 1015
    CouponCodeNotFound = 1016
    InvalidContainerItem = 1017
    ContainerNotOwned = 1018
    KeyNotOwned = 1019
    InvalidItemIdInTable = 1020
    InvalidReceipt = 1021
    ReceiptAlreadyUsed = 1022
    ReceiptCancelled = 1023
    GameNotFound = 1024
    GameModeNotFound = 1025
    InvalidGoogleToken = 1026
    UserIsNotPartOfDeveloper = 1027
    InvalidTitleForDeveloper = 1028
    TitleNameConflicts = 1029
    UserisNotValid = 1030
    ValueAlreadyExists = 1031
    BuildNotFound = 1032
    PlayerNotInGame = 1033
    InvalidTicket = 1034
    InvalidDeveloper = 1035
    InvalidOrderInfo = 1036
    RegistrationIncomplete = 1037
    InvalidPlatform = 1038
    UnknownError = 1039
    SteamApplicationNotOwned = 1040
    WrongSteamAccount = 1041
    TitleNotActivated = 1042
    RegistrationSessionNotFound = 1043
    NoSuchMod = 1044
    FileNotFound = 1045
    DuplicateEmail = 1046
    ItemNotFound = 1047
    ItemNotOwned = 1048
    ItemNotRecycleable = 1049
    ItemNotAffordable = 1050
    InvalidVirtualCurrency = 1051
    WrongVirtualCurrency = 1052
    WrongPrice = 1053
    NonPositiveValue = 1054
    InvalidRegion = 1055
    RegionAtCapacity = 1056
    ServerFailedToStart = 1057
    NameNotAvailable = 1058
    InsufficientFunds = 1059
    InvalidDeviceID = 1060
    InvalidPushNotificationToken = 1061
    NoRemainingUses = 1062
    InvalidPaymentProvider = 1063
    PurchaseInitializationFailure = 1064
    DuplicateUsername = 1065
    InvalidBuyerInfo = 1066
    NoGameModeParamsSet = 1067
    BodyTooLarge = 1068
    ReservedWordInBody = 1069
    InvalidTypeInBody = 1070
    InvalidRequest = 1071
    ReservedEventName = 1072
    InvalidUserStatistics = 1073
    NotAuthenticated = 1074
    StreamAlreadyExists = 1075
    ErrorCreatingStream = 1076
    StreamNotFound = 1077
    InvalidAccount = 1078
    PurchaseDoesNotExist = 1080
    InvalidPurchaseTransactionStatus = 1081
    APINotEnabledForGameClientAccess = 1082
    NoPushNotificationARNForTitle = 1083
    BuildAlreadyExists = 1084
    BuildPackageDoesNotExist = 1085
    BuildIsActive = 1086
    CustomAnalyticsEventsNotEnabledForTitle = 1087
    InvalidSharedGroupId = 1088
    NotAuthorized = 1089
    MissingTitleGoogleProperties = 1090
    InvalidItemProperties = 1091
    InvalidPSNAuthCode = 1092
    InvalidItemId = 1093
    PushNotEnabledForAccount = 1094
    PushServiceError = 1095
