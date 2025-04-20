from django.utils import timezone
from rest_framework import serializers
from .models import Product, ProductPhoto, Bid,Category
from rest_framework.exceptions import ValidationError


class ProductPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPhoto
        fields = ['id', 'photo']





class ProductSerializer(serializers.ModelSerializer):
    photos = ProductPhotoSerializer(many=True, read_only=True)
    seller_name = serializers.CharField(source='seller.name', read_only=True)

    price = serializers.FloatField(
        error_messages={'invalid': '⚠️ السعر يجب أن يكون رقمًا صالحًا.'},
        required=False
    )
    starting_price = serializers.FloatField(
        error_messages={'invalid': '⚠️ السعر الابتدائي يجب أن يكون رقمًا صالحًا.'},
        required=False
    )
    buy_now_price = serializers.FloatField(
        error_messages={'invalid': '⚠️ سعر الشراء الفوري يجب أن يكون رقمًا صالحًا.'},
        required=False
    )
    duration = serializers.IntegerField(
        error_messages={
            'invalid': '⚠️ مدة المزاد يجب أن تكون عددًا صحيحًا.',
            'max_value': '⚠️ مدة المزاد طويلة جدًا.',
            'min_value': '⚠️ مدة المزاد يجب أن تكون أكبر من الصفر.'
        },
        required=False
    )

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'description', 'price', 'starting_price', 'buy_now_price',
            'duration', 'bid_end_time', 'closed', 'currency', 'condition', 'location',
            'is_approved', 'sale_type', 'seller', 'seller_name', 'photos', 'category',
            'is_in_history', 'closed_at'
        ]
        read_only_fields = ['id', 'is_approved', 'seller', 'bid_end_time', 'closed']

    def to_internal_value(self, data):
        errors = []

        required_fields = ["title", "description", "location"]
        for field_name in required_fields:
            value = data.get(field_name)
            if not value:
                errors.append(f"⚠️ الحقل {field_name} لا يمكن أن يكون فارغًا.")

        if data.get("title") and len(data.get("title")) > 100:
            errors.append("⚠️ العنوان يجب أن يحتوي على أقل من 100 حرف.")

        if data.get("location") and len(data.get("location")) > 50:
            errors.append("⚠️ الموقع يجب أن يحتوي على أقل من 50 حرف.")

        if data.get("price") and len(str(data.get("price"))) > 10:
            errors.append("⚠️ السعر يجب أن يحتوي على 10 أرقام كحد أقصى.")

        if errors:
            raise serializers.ValidationError({"error": errors[0]})

        return super().to_internal_value(data)

    def validate(self, data):
        errors = []

        title = data.get('title')
        if not title or len(title) > 100:
            errors.append("⚠️ العنوان مطلوب ويجب أن يحتوي على أقل من 100 حرف.")

        description = data.get('description')
        if not description:
            errors.append("⚠️ الوصف لا يمكن أن يكون فارغًا.")

        price = data.get('price')
        sale_type = data.get('sale_type')
        if sale_type == "عادي" and (price is None or price <= 0):
            errors.append("⚠️ السعر مطلوب ويجب أن يكون أكبر من الصفر في المنتجات العادية.")

        starting_price = data.get('starting_price')
        buy_now_price = data.get('buy_now_price')
        duration = data.get('duration')

        if sale_type == "مزاد":
            if starting_price is None or starting_price <= 0:
                errors.append("⚠️ السعر الابتدائي مطلوب ويجب أن يكون أكبر من الصفر في المزادات.")

            if buy_now_price and buy_now_price <= starting_price:
                errors.append("⚠️ سعر الشراء الفوري يجب أن يكون أعلى من السعر الابتدائي.")

            if duration is None or duration <= 0:
                errors.append("⚠️ مدة المزاد مطلوبة ويجب أن تكون أكبر من الصفر.")

        currency = data.get('currency')
        valid_currencies = dict(Product.CURRENCY_CHOICES).keys()
        if currency not in valid_currencies:
            errors.append("⚠️ العملة غير صالحة.")

        condition = data.get('condition')
        valid_conditions = dict(Product.CONDITION_CHOICES).keys()
        if condition not in valid_conditions:
            errors.append("⚠️ الحالة غير صالحة.")

        valid_sale_types = dict(Product.SALE_TYPE_CHOICES).keys()
        if sale_type not in valid_sale_types:
            errors.append("⚠️ نوع البيع غير صالح.")

        location = data.get('location')
        if not location or len(location) > 50:
            errors.append("⚠️ الموقع مطلوب ويجب أن يكون أقل من 50 حرف.")

        category = data.get('category')
        if sale_type != "مزاد" and not category:
            errors.append("⚠️ الفئة مطلوبة.")

        closed = data.get('closed')
        closed_at = data.get('closed_at')
        if closed and not closed_at:
            errors.append("⚠️ يجب تحديد وقت الإغلاق عند إغلاق المنتج.")

        bid_end_time = data.get('bid_end_time')
        if bid_end_time and bid_end_time <= timezone.now():
            errors.append("⚠️ وقت انتهاء المزاد يجب أن يكون في المستقبل.")

        if errors:
            raise serializers.ValidationError({"error": errors[0]})

        return data
    
    def to_representation(self, instance):
        data = super().to_representation(instance)

        def format_price(value):
            if value is not None:
                return "{:,.0f}".format(value).replace(",", ".")
            return value

        data['price'] = format_price(instance.price)
        data['starting_price'] = format_price(instance.starting_price)
        data['buy_now_price'] = format_price(instance.buy_now_price)

        return data



class BidSerializer(serializers.ModelSerializer):
    buyer_name = serializers.CharField(source='buyer.name', read_only=True)
    product_name = serializers.CharField(source='product.title', read_only=True)
    seller_name = serializers.CharField(source='product.seller.user.username', read_only=True)
    amount = serializers.SerializerMethodField()

    class Meta:
        model = Bid
        fields = ['id', 'product', 'buyer', 'buyer_name', 'product_name', 'seller_name', 'amount', 'status', 'created_at']
        read_only_fields = ['id', 'buyer', 'buyer_name', 'product_name', 'seller_name', 'created_at']

    def get_amount(self, obj):
        return f"{obj.amount:,.0f}".replace(",", ".")



class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'image']