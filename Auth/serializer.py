from rest_framework import serializers
from django.contrib.auth.models import User, Group
from .models import MarketUser
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed

class MarketUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=6,
        error_messages={
            "min_length": "يجب أن تحتوي كلمة المرور على الاقل 6 أحرف .",
        }
    )
    email = serializers.EmailField(
        required=True,
        error_messages={"required": "البريد الإلكتروني مطلوب.", "invalid": "يرجى إدخال بريد إلكتروني صالح."}
    )
    phone = serializers.CharField(
        required=True,
        max_length=20,
        error_messages={"required": "رقم الهاتف مطلوب.", "max_length": "يجب ألا يتجاوز رقم الهاتف 20 رقمًا."}
    )

    class Meta:
        model = MarketUser
        fields = ['password', 'name', 'phone', 'email']

    def validate_email(self, value):
        """التحقق مما إذا كان البريد الإلكتروني موجودًا بالفعل."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("البريد الإلكتروني مسجل بالفعل.")
        return value

    def validate_phone(self, value):
        """التحقق مما إذا كان رقم الهاتف موجودًا بالفعل."""
        if MarketUser.objects.filter(phone=value).exists():
            raise serializers.ValidationError("رقم الهاتف مسجل بالفعل.")
        return value

    def create(self, validated_data):
        email = validated_data.get('email')
        password = validated_data.get('password')

        # إنشاء المستخدم في جدول User المدمج في Django
        user = User.objects.create_user(
            username=email,  # استخدام البريد الإلكتروني كاسم مستخدم
            email=email,
            password=password
        )

        # إضافة المستخدم إلى مجموعة "User"
        user_group, _ = Group.objects.get_or_create(name="User")
        user.groups.add(user_group)

        # إنشاء الملف الشخصي لمستخدم السوق MarketUser
        market_user = MarketUser.objects.create(
            profile=user,
            name=validated_data.get('name'),
            phone=validated_data.get('phone'),
            email=email,
            is_verified = True
        )

        return market_user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketUser
        fields = ['id', 'name', 'phone', 'email', 'profile_picture', 'is_verified', 'is_banned']


class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketUser
        fields = ['name', 'phone', 'email', 'profile_picture']
        extra_kwargs = {
            'phone': {'required': False, 'error_messages': {"invalid": "رقم الهاتف غير صالح."}},
            'email': {'required': False, 'error_messages': {"invalid": "يرجى إدخال بريد إلكتروني صالح."}},
            'name': {'required': False, 'error_messages': {"invalid": "يرجى إدخال اسم صالح."}},
            'profile_picture': {'required': False, 'error_messages': {"invalid": "رابط الصورة غير صالح."}},
        }

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.email = validated_data.get('email', instance.email)
        instance.profile_picture = validated_data.get('profile_picture', instance.profile_picture)
        instance.profile.username = instance.email
        instance.profile.save() 
        instance.save() 
        return instance

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        # التحقق مما إذا كان اسم المستخدم موجودًا
        user = User.objects.filter(username=username).first()
        if not user:
            raise AuthenticationFailed("⚠️ اسم المستخدم غير موجود. الرجاء التحقق من المدخلات.")

        # التحقق من كلمة المرور
        if not user.check_password(password):
            raise AuthenticationFailed("❌ كلمة المرور غير صحيحة. الرجاء المحاولة مرة أخرى.")

        # إذا كان كل شيء صحيحًا، تابع التحقق العادي
        return super().validate(attrs)
    



class UpdateProfilePictureSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketUser
        fields = ['profile_picture']


class UpdatePhoneNumberSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)

class ConfirmPhoneUpdateSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    status = serializers.BooleanField()