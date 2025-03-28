from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from .models import Product, ProductPhoto, Bid,Notificationbid,Listing
from .serializer import ProductSerializer, ProductPhotoSerializer, BidSerializer,CategorySerializer
from django.shortcuts import get_object_or_404
from decorators import verified_user_required ,not_banned_user_required
from .utils import send_real_time_notification,start_conversation
from datetime import timedelta  
from django.utils import timezone  
from .models import Category
from django.db.models import Max
from Auth.models import MarketUser
from decorators import admin_required
from django.db.models import Q, F, Value
from django.db.models.functions import Coalesce
from django.utils.timezone import now



class CustomPagination(PageNumberPagination):
    page_size = 10  # Default items per page
    page_size_query_param = 'page_size'
    max_page_size = 100  # Limit max items per page

@swagger_auto_schema(
    method='post',
    operation_description="Create a new bid product",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['title', 'description', 'starting_price', 'buy_now_price', 'duration', 'condition', 'location', 'currency'],
        properties={
            'title': openapi.Schema(type=openapi.TYPE_STRING, description="Name of the product"),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description="Detailed description of the product"),
            'starting_price': openapi.Schema(type=openapi.TYPE_NUMBER, format=openapi.FORMAT_DECIMAL, description="Initial bidding price"),
            'buy_now_price': openapi.Schema(type=openapi.TYPE_NUMBER, format=openapi.FORMAT_DECIMAL, description="Price to buy instantly"),
            'duration': openapi.Schema(type=openapi.TYPE_INTEGER, description="Duration of the bid in hours"),
            'condition': openapi.Schema(type=openapi.TYPE_STRING, enum=['new', 'used'], description="Product condition"),
            'location': openapi.Schema(type=openapi.TYPE_STRING, description="Product location"),
            'currency': openapi.Schema(type=openapi.TYPE_STRING, enum=['USD', 'LBP'], description="Currency (USD or LBP)"),
            'photos': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING, format=openapi.FORMAT_BINARY), description="Product photos"),
        },
    ),
    responses={
        201: openapi.Response("Product created successfully", ProductSerializer),
        400: "Bad Request - Missing or invalid fields",
        401: "Unauthorized - User not authenticated",
        403: "Forbidden - User not verified or banned",
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@verified_user_required
@not_banned_user_required
def create_bid_product(request):
    seller = request.user.marketuser

    # Extracting non-file data separately
    data = {key: value for key, value in request.data.items() if key not in request.FILES}
    
    # Ensure this is a bid
    data['sale_type'] = 'مزاد'

    # Validate required fields for a bid
    required_fields = ['starting_price', 'duration']
    for field in required_fields:
        if field not in data or not data[field]:
            return Response({"error": f"حقل {field} مطلوب لإضافة منتج في المزاد."}, status=status.HTTP_400_BAD_REQUEST)

    # Get uploaded photos
    photos = request.FILES.getlist('photos')

    # Validate that at least 1 photo and at most 5 photos are provided
    if not photos:
        return Response({"error": "يجب تحميل صورة واحدة على الأقل."}, status=status.HTTP_400_BAD_REQUEST)
    
    if len(photos) > 5:
        return Response({"error": "يمكنك تحميل 5 صور كحد أقصى."}, status=status.HTTP_400_BAD_REQUEST)

    product_serializer = ProductSerializer(data=data, context={'seller': seller})
    if product_serializer.is_valid():
        product = product_serializer.save(seller=seller)
        product.bid_end_time = timezone.now() + timedelta(hours=int(data['duration']))
        product.save()

        # Save uploaded photos
        for photo in photos:
            ProductPhoto.objects.create(product=product, photo=photo)

        return Response(product_serializer.data, status=status.HTTP_201_CREATED)

    return Response(product_serializer.errors, status=status.HTTP_400_BAD_REQUEST)





@swagger_auto_schema(
    method='post',
    operation_description="Create a new simple product (non-bidding product).",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['title', 'description', 'price', 'condition', 'location', 'currency', 'category'],
        properties={
            'title': openapi.Schema(type=openapi.TYPE_STRING, description="Name of the product"),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description="Detailed description of the product"),
            'price': openapi.Schema(type=openapi.TYPE_NUMBER, format=openapi.FORMAT_DECIMAL, description="Price of the product"),
            'condition': openapi.Schema(type=openapi.TYPE_STRING, enum=['جدسد', 'مستعمل'], description="Product condition"),
            'location': openapi.Schema(type=openapi.TYPE_STRING, description="Product location"),
            'currency': openapi.Schema(type=openapi.TYPE_STRING, enum=['دولار أمريكي', 'الليرة اللبنانية (ل.ل)'], description="Currency (USD or LBP)"),
            'category': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the product category"),
            'photos': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_STRING, format=openapi.FORMAT_BINARY),
                description="Array of product photos (optional)"
            ),
        },
    ),
    responses={
        201: openapi.Response("Product created successfully", ProductSerializer),
        400: "Bad Request - Missing or invalid fields",
        401: "Unauthorized - User not authenticated",
        403: "Forbidden - User not verified or banned",
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@verified_user_required
@not_banned_user_required
def create_simple_product(request):
    seller = request.user.marketuser

    # Extracting non-file data separately
    data = {key: value for key, value in request.data.items() if key not in request.FILES}

    data['sale_type'] = 'عادي'

    # Validate category existence and type
    category_id = data.get('category')
    if not category_id:
        return Response({"error": "التصنيف مطلوب."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        category_id = int(category_id)  # Ensure it's an integer
        category = Category.objects.get(pk=category_id)
    except (ValueError, Category.DoesNotExist):
        return Response({"error": "رقم التصنيف غير صالح."}, status=status.HTTP_400_BAD_REQUEST)

    # Validate price field
    if 'price' not in data or not data['price']:
        return Response({"error": "السعر مطلوب للمنتجات العادية."}, status=status.HTTP_400_BAD_REQUEST)

    # Handle file uploads separately
    photos = request.FILES.getlist('photos')

    if not photos:
        return Response({"error": "يجب تحميل صورة واحدة على الأقل."}, status=status.HTTP_400_BAD_REQUEST)

    if len(photos) > 5:
        return Response({"error": "يمكنك تحميل 5 صور كحد أقصى."}, status=status.HTTP_400_BAD_REQUEST)

    # Serialize product
    product_serializer = ProductSerializer(data=data, context={'seller': seller, 'category': category})

    if product_serializer.is_valid():
        product = product_serializer.save(seller=seller)

        # Save uploaded photos
        for photo in photos:
            ProductPhoto.objects.create(product=product, photo=photo)

        return Response(product_serializer.data, status=status.HTTP_201_CREATED)

    return Response(product_serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@swagger_auto_schema(
    method='post',
    operation_description="تقديم مزايدة على منتج معين في المزاد.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["amount"],
        properties={
            "amount": openapi.Schema(
                type=openapi.TYPE_NUMBER,
                description="قيمة المزايدة الجديدة (يجب أن تكون أعلى من أعلى مزايدة حالية)."
            ),
        },
    ),
    responses={
        201: openapi.Response(
            description="تم تقديم المزايدة بنجاح وهي قيد المراجعة من قبل الإدارة.",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(type=openapi.TYPE_STRING, description="رسالة النجاح."),
                    "bid": openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        description="تفاصيل المزايدة المقدمة.",
                    ),
                },
            ),
        ),
        400: openapi.Response(
            description="طلب غير صالح، تحقق من الرسائل لمعرفة الأخطاء.",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "error": openapi.Schema(type=openapi.TYPE_STRING, description="تفاصيل الخطأ."),
                },
            ),
        ),
        404: openapi.Response(
            description="المنتج غير متاح للمزايدة.",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "error": openapi.Schema(type=openapi.TYPE_STRING, description="تفاصيل الخطأ."),
                },
            ),
        ),
    },
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@verified_user_required
@not_banned_user_required
def place_bid(request, product_id):
    # Get the product and ensure it’s a bid product
    product = Product.objects.filter(id=product_id, sale_type='مزاد', is_approved=True).first()
    if not product:
        return Response({"error": "المنتج غير متاح للمزايدة."}, status=status.HTTP_404_NOT_FOUND)

    # Prevent the seller from bidding on their own product
    if product.seller == request.user.marketuser:
        return Response({"error": "لا يمكنك المزايدة على منتجك الخاص."}, status=status.HTTP_400_BAD_REQUEST)

    # Check if bidding has ended
    if product.closed or (product.bid_end_time and timezone.now() >= product.bid_end_time):
        product.closed = True
        product.save()
        return Response({"error": "انتهت فترة المزايدة على هذا المنتج."}, status=status.HTTP_400_BAD_REQUEST)

    # Get the bid amount
    bid_amount = request.data.get("amount")
    if not bid_amount:
        return Response({"error": "يجب تحديد قيمة المزايدة."}, status=status.HTTP_400_BAD_REQUEST)

    bid_amount = float(bid_amount)

    # Get the highest accepted bid (or starting price if no bids exist)
    highest_bid = Bid.objects.filter(product=product, status="accepted").aggregate(Max('amount'))['amount__max'] or product.starting_price
    if bid_amount <= highest_bid:
        return Response({"error": f"يجب أن تكون المزايدة أعلى من {highest_bid} {product.currency}."}, status=status.HTTP_400_BAD_REQUEST)

    # Create the new bid with `pending` status (Admin will approve)
    bid = Bid.objects.create(
        product=product,
        buyer=request.user.marketuser,
        amount=bid_amount,
        status="pending"  # Pending approval
    )

    # Notify the user that their bid is under review
    send_real_time_notification(
        request.user.marketuser,
        f"تم تقديم مزايدتك بقيمة {bid_amount} {product.currency} على '{product.title}' وهي قيد المراجعة من قبل الإدارة."
    )

    # Notify admins for bid approval
    admin_users = MarketUser.objects.filter(profile__groups__name="Admin")
    for admin in admin_users:
        send_real_time_notification(
            admin,
            f"تم تقديم مزايدة جديدة بقيمة {bid_amount} {product.currency} على '{product.title}'. يرجى مراجعتها والموافقة عليها."
        )

    return Response(
        {
            "message": "تم تقديم المزايدة بنجاح وهي قيد المراجعة من قبل الإدارة.",
            "bid": BidSerializer(bid).data
        },
        status=status.HTTP_201_CREATED
    )


@swagger_auto_schema(
    method='post',
    operation_summary="إنهاء المزاد وتحديد الفائز",
    operation_description="""
    يقوم البائع بإنهاء المزاد واختيار المزايدة الفائزة. يتم رفض جميع المزايدات الأخرى، ويتم إشعار الفائز والبائع والمسؤولين الإداريين.
    """,
    manual_parameters=[
        openapi.Parameter(
            name="Authorization",
            in_=openapi.IN_HEADER,
            description="توكن المصادقة باستخدام JWT (Bearer token)",
            type=openapi.TYPE_STRING,
            required=True
        ),
    ],
    responses={
        200: openapi.Response(
            description="تم إنهاء المزاد بنجاح",
            examples={
                "application/json": {
                    "message": "تم إنهاء المزاد بنجاح.",
                    "winning_bid": {
                        "id": 12,
                        "amount": 1500,
                        "buyer": {
                            "id": 5,
                            "username": "mohammed123"
                        },
                        "status": "accepted",
                        "winner": True
                    }
                }
            }
        ),
        400: openapi.Response(
            description="خطأ في الإدخال",
            examples={
                "application/json": {
                    "error": "لم يتم تحديد المزايدة الفائزة. يرجى اختيار مزايدة لإنهاء المزاد."
                }
            }
        ),
        404: openapi.Response(
            description="المنتج أو المزايدة غير موجودة",
            examples={
                "application/json": {
                    "error": "المنتج غير موجود أو ليس لديك الصلاحية لإنهاء المزاد."
                }
            }
        )
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@verified_user_required
@not_banned_user_required
def end_bid(request, product_id, bid_id):
    seller = request.user.marketuser

    try:
        # التأكد من أن المنتج موجود وينتمي للبائع
        product = Product.objects.get(id=product_id, seller=seller, sale_type='مزاد')
    except Product.DoesNotExist:
        return Response({"error": "المنتج غير موجود أو ليس لديك الصلاحية لإنهاء المزاد."}, status=status.HTTP_404_NOT_FOUND)

    if not bid_id:
        return Response({"error": "لم يتم تحديد المزايدة الفائزة. يرجى اختيار مزايدة لإنهاء المزاد."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # البحث عن المزايدة الفائزة والتأكد من أنها مقبولة
        selected_bid = Bid.objects.get(id=bid_id, product=product, status="accepted")
    except Bid.DoesNotExist:
        return Response({"error": "المزايدة المحددة غير موجودة أو لم يتم قبولها أو لا تتعلق بهذا المنتج."}, status=status.HTTP_404_NOT_FOUND)

    # تعيين المزايدة الفائزة
    selected_bid.winner = True
    selected_bid.save()

    # تحديث حالة المنتج ليكون مبيعًا ومغلقًا
    product.sold = True
    product.closed = True
    product.save()

    # رفض جميع المزايدات الأخرى لهذا المنتج
    Bid.objects.filter(product=product).exclude(id=selected_bid.id).update(status="rejected", winner=False)

    # 🔔 إرسال إشعار للفائز
    send_real_time_notification(
        selected_bid.buyer, 
        f"🎉 تهانينا! لقد فزت بالمزاد على '{product.title}' بمبلغ {selected_bid.amount} {product.currency}."
    )

    # 🔔 إرسال إشعار للبائع
    send_real_time_notification(
        product.seller, 
        f"✅ لقد قمت ببيع '{product.title}' بنجاح بمبلغ {selected_bid.amount} {product.currency}."
    )

    # 💬 بدء محادثة بين البائع والفائز
    start_conversation(product.seller, selected_bid.buyer, product)

    # 🔍 العثور على جميع المسؤولين الإداريين
    admin_users = MarketUser.objects.filter(user__groups__name="Admin")

    # 🔔 إشعار المسؤولين بانتهاء المزاد
    for admin in admin_users:
        send_real_time_notification(
            admin, 
            f"📢 انتهى المزاد على '{product.title}'. المزايدة الفائزة: {selected_bid.amount} {product.currency}."
        )

    return Response({
        "message": "تم إنهاء المزاد بنجاح.",
        "winning_bid": BidSerializer(selected_bid).data
    }, status=status.HTTP_200_OK)



@swagger_auto_schema(
    method='get',
    operation_summary="عرض جميع المنتجات الخاصة بالبائع",
    operation_description="""
    يقوم هذا الطلب بجلب جميع المنتجات التي تم إدراجها من قبل البائع المسجل حاليًا. يتم ترتيب المنتجات من الأحدث إلى الأقدم.
    """,
    manual_parameters=[
        openapi.Parameter(
            name="Authorization",
            in_=openapi.IN_HEADER,
            description="توكن المصادقة باستخدام JWT (Bearer token)",
            type=openapi.TYPE_STRING,
            required=True
        ),
    ],
    responses={
        200: openapi.Response(
            description="تم استرجاع المنتجات بنجاح",
            examples={
                "application/json": [
                    {
                        "id": 1,
                        "title": "هاتف آيفون 13",
                        "price": 1200,
                        "currency": "USD",
                        "sale_type": "عادي",
                        "created_at": "2025-02-22T12:00:00Z"
                    },
                    {
                        "id": 2,
                        "title": "كمبيوتر محمول HP",
                        "price": 900,
                        "currency": "USD",
                        "sale_type": "مزاد",
                        "created_at": "2025-02-20T15:30:00Z"
                    }
                ]
            }
        ),
        404: openapi.Response(
            description="لم يتم العثور على منتجات",
            examples={
                "application/json": {
                    "message": "لم يتم العثور على أي منتجات."
                }
            }
        ),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@verified_user_required
@not_banned_user_required
def seller_products_history(request):
    """
    استرجاع جميع المنتجات التي تم إدراجها من قبل البائع المسجل حاليًا.
    """
    seller = request.user.marketuser
    products = Product.objects.filter(seller=seller).order_by('-created_at')

    if not products.exists():
        return Response({"message": "لم يتم العثور على أي منتجات."}, status=status.HTTP_404_NOT_FOUND)

    return Response(ProductSerializer(products, many=True).data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    operation_summary="عرض جميع المزايدات على منتج معين",
    operation_description="""
    يقوم هذا الطلب بجلب جميع المزايدات التي تم تقديمها على منتج معين من قبل البائع المسجل حاليًا.
    يتم ترتيب المزايدات من الأعلى إلى الأدنى من حيث القيمة.
    """,
    manual_parameters=[
        openapi.Parameter(
            name="Authorization",
            in_=openapi.IN_HEADER,
            description="توكن المصادقة باستخدام JWT (Bearer token)",
            type=openapi.TYPE_STRING,
            required=True
        ),
        openapi.Parameter(
            name="product_id",
            in_=openapi.IN_PATH,
            description="معرّف المنتج المطلوب عرض المزايدات الخاصة به",
            type=openapi.TYPE_INTEGER,
            required=True
        ),
    ],
    responses={
        200: openapi.Response(
            description="تم استرجاع المزايدات بنجاح",
            examples={
                "application/json": [
                    {
                        "id": 101,
                        "buyer": {
                            "id": 5,
                            "username": "ahmed_user"
                        },
                        "amount": 1500,
                        "status": "accepted",
                        "winner": False,
                        "created_at": "2025-02-22T12:00:00Z"
                    },
                    {
                        "id": 102,
                        "buyer": {
                            "id": 7,
                            "username": "sara_bidder"
                        },
                        "amount": 1400,
                        "status": "pending",
                        "winner": False,
                        "created_at": "2025-02-21T18:30:00Z"
                    }
                ]
            }
        ),
        404: openapi.Response(
            description="لم يتم العثور على المزايدات",
            examples={
                "application/json": {
                    "message": "لم يتم تقديم أي مزايدات على هذا المنتج بعد."
                }
            }
        ),
        403: openapi.Response(
            description="البائع لا يملك الصلاحية لعرض المزايدات على هذا المنتج",
            examples={
                "application/json": {
                    "error": "المنتج غير موجود أو ليس لديك الإذن لعرض المزايدات."
                }
            }
        ),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@verified_user_required
@not_banned_user_required
def product_bids_history(request, product_id):
    """
    استرجاع جميع المزايدات التي تم تقديمها على منتج معين من قبل البائع المسجل حاليًا.
    """
    seller = request.user.marketuser

    try:
        product = Product.objects.get(id=product_id, seller=seller, sale_type='مزاد')
    except Product.DoesNotExist:
        return Response({"error": "المنتج غير موجود أو ليس لديك الإذن لعرض المزايدات."}, status=status.HTTP_404_NOT_FOUND)

    bids = Bid.objects.filter(product=product).order_by('-amount')

    if not bids.exists():
        return Response({"message": "لم يتم تقديم أي مزايدات على هذا المنتج بعد."}, status=status.HTTP_404_NOT_FOUND)

    return Response(BidSerializer(bids, many=True).data, status=status.HTTP_200_OK)




@swagger_auto_schema(
    method='get',
    operation_description="Retrieve all bids for a specific product.",
    responses={
        200: openapi.Response('List of bids', BidSerializer(many=True)),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@verified_user_required
@not_banned_user_required
def get_product_bids(request, product_id):
    try:
        product = Product.objects.get(id=product_id, seller=request.user.marketuser)
    except Product.DoesNotExist:
        return Response({"error": "Product not found or you do not have permission to view its bids."}, status=status.HTTP_404_NOT_FOUND)

    bids = Bid.objects.filter(product=product).order_by('-amount')
    serializer = BidSerializer(bids, many=True)
    return Response(serializer.data)


# Other existing views like delete_product, update_product, etc., remain unchanged.

class ProductPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

@swagger_auto_schema(
    method='get',
    operation_description="Retrieve all approved products with optional filtering by sale type, category, price range, and title.",
    manual_parameters=[
        openapi.Parameter('sale_type', openapi.IN_QUERY, description="Sale type (simple/bid)", type=openapi.TYPE_STRING),
        openapi.Parameter('category', openapi.IN_QUERY, description="Category name to filter products", type=openapi.TYPE_STRING),
        openapi.Parameter('min_price', openapi.IN_QUERY, description="Minimum price to filter products", type=openapi.TYPE_NUMBER),
        openapi.Parameter('max_price', openapi.IN_QUERY, description="Maximum price to filter products", type=openapi.TYPE_NUMBER),
        openapi.Parameter('title', openapi.IN_QUERY, description="Search for products by title (case-insensitive)", type=openapi.TYPE_STRING),
    ],
    responses={
        200: openapi.Response('Paginated list of products', ProductSerializer(many=True)),
    }
)

@api_view(['GET'])
def list_products(request):
    """
    استرجاع قائمة المنتجات مع إمكانية التصفية والفرز حسب السعر
    وإضافة قائمة العروض (bids) إذا كان المنتج من نوع bid
    مع التحقق من انتهاء المزادات وإغلاقها
    """
    sale_type = request.query_params.get('sale_type', None)
    category_id = request.query_params.get('category', None)
    min_price = request.query_params.get('min_price', None)
    max_price = request.query_params.get('max_price', None)
    price_order = request.query_params.get('price_order', None)  # 'asc' or 'desc'
    title = request.query_params.get('title', None)

    products = Product.objects.filter(is_approved=True, sold=False)

    # Close expired bids
    Product.objects.filter(
        sale_type="مزاد",
        closed=False,
        bid_end_time__lte=now()
    ).update(closed=True, closed_at=now())

    # Apply filters
    if sale_type:
        products = products.filter(sale_type=sale_type)
    if category_id:
        products = products.filter(category_id=category_id)

    # Apply min price filtering (either price or starting_price)
    if min_price:
        products = products.filter(
            Q(price__gte=min_price) | Q(starting_price__gte=min_price)
        )

    # Apply max price filtering (either price or starting_price)
    if max_price:
        products = products.filter(
            Q(price__lte=max_price) | Q(starting_price__lte=max_price)
        )

    # Sorting by price (lowest available price)
    if price_order == "Min":
        products = products.annotate(
            effective_price=Coalesce('price', 'starting_price')
        ).order_by("effective_price")
    elif price_order == "Max":
        products = products.annotate(
            effective_price=Coalesce('price', 'starting_price')
        ).order_by("-effective_price")

    if title:
        products = products.filter(title__icontains=title)

    # Apply pagination
    paginator = CustomPagination()
    paginated_products = paginator.paginate_queryset(products, request)

    # Serialize products with seller, category, and bids (if applicable)
    serialized_products = []
    for product in paginated_products:
        serialized_product = ProductSerializer(product).data
        seller = product.seller
        category = product.category
        
        serialized_product["seller"] = {
            "id": seller.id,
            "name": seller.name,
            "profile_picture": seller.profile_picture.url if seller.profile_picture else None,
            "phone_number": seller.phone
        }
        
        serialized_product["category"] = {
            "id": category.pk if category else None,
            "name": category.name if category else "No Category"
        }

        # If the product is a bid, include all bids for it
        if product.sale_type == "مزاد":
            bids = Bid.objects.filter(product=product).order_by("-amount")
            serialized_product["bids"] = BidSerializer(bids, many=True).data

        serialized_products.append(serialized_product)

    return paginator.get_paginated_response(serialized_products)




@api_view(['GET'])
def admin_list_products(request):
    """
    استرجاع قائمة المنتجات للمسؤول مع إمكانية التصفية والفرز حسب السعر وحالة الموافقة
    """
    sale_type = request.query_params.get('sale_type', None)
    category_id = request.query_params.get('category', None)
    min_price = request.query_params.get('min_price', None)
    max_price = request.query_params.get('max_price', None)
    condition = request.query_params.get('condition',None)
    price_order = request.query_params.get('price_order', None)  # 'asc' or 'desc'
    title = request.query_params.get('title', None)
    is_approved = request.query_params.get('is_approved', None)  # Filter by approval status

    statuse = None
    if is_approved == "true":
        statuse = True
    elif is_approved == "false":
        statuse = False

    products = Product.objects.all()

    # Apply filters
    if condition:
        products = products.filter(condition=condition)
    if sale_type:
        products = products.filter(sale_type=sale_type)
    if category_id:
        products = products.filter(category_id=category_id)
    if is_approved:
        products = products.filter(is_approved=statuse)

    if min_price:
        products = products.filter(
            Q(price__gte=min_price) | Q(starting_price__gte=min_price)
        )

    if max_price:
        products = products.filter(
            Q(price__lte=max_price) | Q(starting_price__lte=max_price)
        )

    if price_order == "asc":
        products = products.annotate(
            effective_price=Coalesce('price', 'starting_price')  
        ).order_by("effective_price")
    elif price_order == "desc":
        products = products.annotate(
            effective_price=Coalesce('price', 'starting_price')
        ).order_by("-effective_price")

    if title:
        products = products.filter(title__icontains=title)

    serialized_products = []
    for product in products:
        serialized_product = ProductSerializer(product).data
        seller = product.seller  # Assuming 'seller' is a MarketUser instance
        category = product.category  # Assuming 'category' is a Category instance
        
        serialized_product["seller"] = {
            "id": seller.id,
            "name": seller.name,
            "profile_picture": seller.profile_picture.url if seller.profile_picture else None
        }
        
        # Include category name in the response (handle None case)
        serialized_product["category"] = {
            "name": category.name if category else "No Category"
        }
        
        serialized_products.append(serialized_product)

    return Response(serialized_products, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='patch',
    operation_description="Partially update a product. Only the seller of the product can update it.",
    request_body=ProductSerializer,
    responses={
        200: openapi.Response('Product updated successfully', ProductSerializer),
        400: openapi.Response('Invalid data provided'),
        404: openapi.Response('Product not found or you do not have permission to edit it'),
    }
)
@api_view(['PUT', 'PATCH'])  
@permission_classes([IsAuthenticated])
@verified_user_required
@not_banned_user_required
def update_product(request, product_id):
    seller = request.user.marketuser  

    try:
        product = Product.objects.get(id=product_id, seller=seller)  # Ensure the seller owns the product
    except Product.DoesNotExist:
        return Response({"error": "Product not found or you do not have permission to edit it"}, status=status.HTTP_404_NOT_FOUND)

    data = request.data
    product_serializer = ProductSerializer(product, data=data, partial=True)  # Enable partial updates
    if product_serializer.is_valid():
        product_serializer.save()
        return Response(product_serializer.data)
    return Response(product_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='delete',
    operation_description="Delete a product. Only the seller of the product can delete it.",
    responses={
        200: openapi.Response('Product deleted successfully'),
        404: openapi.Response('Product not found or you do not have permission to delete it'),
    }
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@verified_user_required
@not_banned_user_required
def delete_product(request, product_id):
    seller = request.user.marketuser  # Ensure the user is the seller
    try:
        product = Product.objects.get(id=product_id, seller=seller)
    except Product.DoesNotExist:
        return Response({"error": "Product not found or you do not have permission to delete it."}, status=status.HTTP_404_NOT_FOUND)

    product.delete()
    return Response({"message": "Product deleted successfully."}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    operation_description="Retrieve all products listed by the authenticated seller.",
    responses={
        200: openapi.Response('List of seller products', ProductSerializer(many=True)),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@verified_user_required
@not_banned_user_required
def get_seller_products(request):
    seller = request.user.marketuser
    products = Product.objects.filter(seller=seller).order_by('-upload_date')
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@verified_user_required
@not_banned_user_required
def purchase_product(request, product_id):
    buyer = request.user.marketuser  # Authenticated user

    # Get the product
    product = get_object_or_404(Product, id=product_id, sale_type='عادي')

    # Prevent the seller from purchasing their own product
    if product.seller == buyer:
        return Response({"error": "You cannot purchase your own product."}, status=status.HTTP_400_BAD_REQUEST)

    # Ensure the product is available for sale
    if product.sold:
        return Response({"error": "This product has already been sold."}, status=status.HTTP_400_BAD_REQUEST)

    # Create a new listing
    listing = Listing.objects.create(
        buyer=buyer,
        product=product,
        quantity=1,  # Assuming it's a single-unit purchase
        is_payed=False  # Payment is not yet confirmed
    )

    # Notify the seller
    seller_message = f"Your product '{product.title}' has been requested for purchase by {buyer.profile.username}."
    # Notificationbid.objects.create(
    #     recipient=product.seller,
    #     message=seller_message,
    #     bid=None  # Since this isn't a bid-related notification
    # )

    send_real_time_notification(product.seller, seller_message)
    return Response({
        "message": "Purchase request sent successfully.",
        "listing_id": listing.id
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@verified_user_required
@not_banned_user_required
def accept_related_listings(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)

    if listing.product.seller != request.user.marketuser:
        return Response({"error": "You are not authorized to mark this listing as paid."}, status=status.HTTP_403_FORBIDDEN)
    listing.is_payed = True
    listing.save()
    message = f"Your payment for '{listing.product.title}' has been confirmed by the seller."
    send_real_time_notification(listing.buyer, message)

    return Response({"message": "Listing marked as paid successfully."}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@verified_user_required
@not_banned_user_required
def get_seller_listings(request):
    """Get all listings where the user is the seller (to approve payment)."""
    user = request.user.marketuser  # Get the authenticated MarketUser

    # Get listings where the user is the seller
    seller_listings = Listing.objects.filter(product__seller=user).select_related("product", "buyer")

    listings_data = [
        {
            "id": listing.id,
            "product": listing.product.title,
            "buyer": listing.buyer.profile.username,
            "purchase_date": listing.purchase_date,
            "quantity": listing.quantity,
            "is_payed": listing.is_payed
        }
        for listing in seller_listings
    ]

    return Response({"seller_listings": listings_data}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@verified_user_required
@not_banned_user_required
def get_buyer_purchases(request):
    """Get all listings where the user is the buyer (to see purchases)."""
    user = request.user.marketuser  # Get the authenticated MarketUser

    # Get listings where the user is the buyer
    buyer_listings = Listing.objects.filter(buyer=user).select_related("product")

    listings_data = [
        {
            "id": listing.id,
            "product": listing.product.title,
            "seller": listing.product.seller.profile.username,
            "purchase_date": listing.purchase_date,
            "quantity": listing.quantity,
            "is_payed": listing.is_payed
        }
        for listing in buyer_listings
    ]

    return Response({"buyer_purchases": listings_data}, status=status.HTTP_200_OK)

# 📌 Create a new category
@swagger_auto_schema(
    method='post',
    operation_summary="إضافة تصنيف جديد",
    operation_description="يقوم هذا الطلب بإنشاء تصنيف جديد ببيانات الاسم والوصف والصورة.",
    request_body=CategorySerializer,
    responses={
        201: openapi.Response(
            description="تم إنشاء التصنيف بنجاح",
            examples={
                "application/json": {
                    "id": 1,
                    "name": "إلكترونيات",
                    "description": "منتجات إلكترونية",
                    "image": "/media/Category_pictures/electronics.jpg"
                }
            }
        ),
        400: openapi.Response(
            description="خطأ في الإدخال",
            examples={
                "application/json": {
                    "name": ["هذا الاسم مستخدم بالفعل."]
                }
            }
        ),
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@admin_required
def create_category(request):
    """
    إضافة تصنيف جديد
    """
    serializer = CategorySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 📌 Get all categories
@swagger_auto_schema(
    method='get',
    operation_summary="عرض جميع التصنيفات",
    operation_description="يقوم هذا الطلب بجلب جميع التصنيفات المسجلة في النظام. يمكنك أيضًا البحث عن تصنيف معين باستخدام اسم التصنيف.",
    manual_parameters=[
        openapi.Parameter(
            'search',
            openapi.IN_QUERY,
            description="ابحث عن تصنيف معين باستخدام الاسم (بحث جزئي غير حساس لحالة الأحرف).",
            type=openapi.TYPE_STRING
        )
    ],
    responses={
        200: openapi.Response(
            description="تم استرجاع التصنيفات بنجاح",
            examples={
                "application/json": [
                    {
                        "id": 1,
                        "name": "إلكترونيات",
                        "description": "منتجات إلكترونية",
                        "image": "/media/Category_pictures/electronics.jpg"
                    },
                    {
                        "id": 2,
                        "name": "أزياء",
                        "description": "ملابس وأزياء",
                        "image": "/media/Category_pictures/fashion.jpg"
                    }
                ]
            }
        ),
        404: openapi.Response(
            description="لم يتم العثور على تصنيفات",
            examples={
                "application/json": {
                    "message": "لا توجد تصنيفات متاحة."
                }
            }
        ),
    }
)
@api_view(['GET'])
def get_all_categories(request):
    search_query = request.GET.get('search', '')  # Get search query from request parameters
    categories = Category.objects.filter(name__icontains=search_query) if search_query else Category.objects.all()
    
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


class CustomPagination(PageNumberPagination):
    page_size = 10  # Default items per page
    page_size_query_param = 'page_size'
    max_page_size = 100  # Limit max items per page

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@verified_user_required
@not_banned_user_required
def user_products_and_bids(request):
    user = request.user.marketuser
    sale_type = request.GET.get('sell_type', None)

    user_products = Product.objects.filter(seller=user)

    if sale_type:
        user_products = user_products.filter(sale_type=sale_type)

    now = timezone.now()
    expired_auctions = user_products.filter(
        sale_type="مزاد", closed=True, is_in_history=False, closed_at__lte=now - timezone.timedelta(days=1)
    )

    for product in expired_auctions:
        product.is_in_history = True
        product.save()

    sold_products = user_products.filter(sale_type="عادي", is_approved=True)
    history_products = user_products.filter(sale_type="مزاد", is_in_history=True, is_approved=True)

    filtered_products = sold_products | history_products

    paginator = CustomPagination()
    paginated_products = paginator.paginate_queryset(filtered_products, request)

    # Serialize products
    products_serializer = ProductSerializer(paginated_products, many=True)
    
    # Modify the product response to match your required format
    formatted_products = []
    for product in products_serializer.data:
        formatted_products.append({
            **product,  # Keep original fields
            "seller": {
                "id": product["seller"],
                "name": product["seller_name"],
                "profile_picture": user.profile_picture.url if user.profile_picture else None,
                "phone_number": user.phone
            },
            "category": {
                "id": product["category"] if product["category"] else None,
                "name": "No Category" if product["category"] is None else product["category"]
            },
        })

    # Get user bids
    user_bids = Bid.objects.filter(buyer=user)
    bids_serializer = BidSerializer(user_bids, many=True)

    return paginator.get_paginated_response({
        'user_products': formatted_products,
        'bids': bids_serializer.data,
    })



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can delete categories
def delete_category(request, pk):
    try:
        category = Category.objects.get(pk=pk)
        category.delete()
        return Response({'info': 'Category deleted successfully'}, status=status.HTTP_200_OK)
    except Category.DoesNotExist:
        return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@verified_user_required
@not_banned_user_required
def close_bid(request, product_id):
    """
    Manually close a bid and move it to history.
    """
    try:
        now = timezone.now()
        product = Product.objects.get(id=product_id, sale_type='مزاد', closed=False)

        if product.bid_end_time > now:
            return Response({"error": "Auction is still running."}, status=status.HTTP_400_BAD_REQUEST)

        product.sold = True
        product.closed = True
        product.closed_at = now
        product.save()
        highest_bid = Bid.objects.filter(product=product, status="accepted").order_by('-amount').first()

        if highest_bid:
            highest_bid.winner = True
            highest_bid.save()

            # Notify seller & winner
            send_real_time_notification(product.seller, f"المزاد على {product.title} قد انتهى! الفائز هو {highest_bid.buyer.name}.")
            send_real_time_notification(highest_bid.buyer, f"لقد فزت بالمزاد على {product.title} بمبلغ {highest_bid.amount} {product.currency}.")

            # Create a conversation between seller & winner
            start_conversation(product.seller, highest_bid.buyer, product)
        else:
            send_real_time_notification(product.seller, f"المزاد على {product.title} قد انتهى بدون عروض.")

        return Response({"success": f"Bid closed for {product.title}."}, status=status.HTTP_200_OK)

    except Product.DoesNotExist:
        return Response({"error": "Product not found or already closed."}, status=status.HTTP_404_NOT_FOUND)
    



@api_view(['GET'])
def list_auction_products(request):
    """
    استرجاع قائمة المنتجات من نوع "مزاد" فقط
    """
    # Filter only products that are auctions
    products = Product.objects.filter(is_approved=True, sold=False, sale_type="مزاد")
    
    # Apply pagination
    paginator = CustomPagination()
    paginated_products = paginator.paginate_queryset(products, request)
    
    # Serialize products with seller, category, and bids
    serialized_products = []
    for product in paginated_products:
        serialized_product = ProductSerializer(product).data
        seller = product.seller  # Assuming 'seller' is a MarketUser instance
        category = product.category  # Assuming 'category' is a Category instance
        
        serialized_product["seller"] = {
            "id": seller.id,
            "name": seller.name,
            "profile_picture": seller.profile_picture.url if seller.profile_picture else None,
            "phone_number": seller.phone
        }
        
        # Include category name in the response (handle None case)
        serialized_product["category"] = {
            "id": category.pk if category else None,
            "name": category.name if category else "No Category"
        }
        
        # Include all bids for the auction product
        bids = Bid.objects.filter(product=product).order_by("-amount")  
        serialized_product["bids"] = BidSerializer(bids, many=True).data
        
        serialized_products.append(serialized_product)
    
    return paginator.get_paginated_response(serialized_products)



@api_view(['GET'])
def get_product(request, product_id):
    """
    استرجاع منتج واحد حسب معرفه وإضافة قائمة العروض (bids) إذا كان المنتج من نوع مزاد
    """
    try:
        product = Product.objects.get(id=product_id, is_approved=True, sold=False)
    except Product.DoesNotExist:
        return Response({"detail": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    # Serialize product with seller, category, and bids (if applicable)
    serialized_product = ProductSerializer(product).data
    seller = product.seller  # Assuming 'seller' is a MarketUser instance
    category = product.category  # Assuming 'category' is a Category instance
    
    serialized_product["seller"] = {
        "id": seller.id,
        "name": seller.name,
        "profile_picture": seller.profile_picture.url if seller.profile_picture else None,
        "phone_number": seller.phone
    }
    
    # Include category name in the response (handle None case)
    serialized_product["category"] = {
        "id": category.pk if category else None,
        "name": category.name if category else "No Category"
    }

    # If the product is a bid, include all bids and a separate list of bid amounts
    if product.sale_type == "مزاد":
        bids = Bid.objects.filter(product=product).order_by("-amount")
        serialized_product["bids"] = BidSerializer(bids, many=True).data

        # Extract bid amounts in descending order
        serialized_product["price"] = [bid.amount for bid in bids]

    return Response(serialized_product)