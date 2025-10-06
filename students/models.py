from django.db import models
from datetime import datetime
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Student(models.Model):
    
    class Gender(models.TextChoices):
        MALE = 'male', 'ذكر'
        FEMALE = 'female', 'أنثى'
    
    class HowKnewUs(models.TextChoices):
        FRIEND = 'friend', 'صديق'
        SOCIAL = 'social', 'وسائل التواصل الاجتماعي'
        AD = 'ad', 'إعلان'
        ADS = 'ads', 'إعلانات طرقية'
        OTHER = 'other', 'أخرى'
    
    class Academic_Track(models.TextChoices):
        LITERARY = 'أدبي', 'الأدبي'
        SCIENTIFIC = 'علمي', 'العلمي'
        NINTH_GRADE = 'تاسع', 'الصف التاسع'
    
    # Basic Information
    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=6, choices=Gender.choices, blank=True)
    branch = models.CharField(max_length=10, choices=Academic_Track.choices, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    student_number = models.CharField(max_length=20, blank=True) 
    nationality = models.CharField(max_length=50, blank=True)
    registration_date = models.DateField(default=datetime.now)
    tase3 = models.IntegerField(default=0, blank=True)
    disease = models.TextField(blank=True, default="none")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    # Father Information
    father_name = models.CharField(max_length=100, blank=True)
    father_job = models.CharField(max_length=100, blank=True)
    father_phone = models.CharField(max_length=20, blank=True)
    
    # Mother Information
    mother_name = models.CharField(max_length=100, blank=True)
    mother_job = models.CharField(max_length=100, blank=True)
    mother_phone = models.CharField(max_length=20, blank=True)
    
    # Address Information
    address = models.TextField(blank=True)
    home_phone = models.CharField(max_length=20, blank=True)
    
    # Previous Education
    previous_school = models.CharField(max_length=100, blank=True)
    elementary_school = models.CharField(max_length=100, blank=True)
    
    # Other Information
    how_knew_us = models.CharField(
        max_length=100, 
        choices=HowKnewUs.choices, 
        blank=True, 
        null=True
    )
    notes = models.TextField(blank=True)
    added_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="تم الإضافة بواسطة"
    )
    
    # Discount fields
    discount_percent = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0'),
        help_text="Percentage discount (0-100)",
        verbose_name='نسبة الحسم الافتراضي %'
    )
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0'),
        help_text="Fixed amount discount",
        verbose_name='قيمة الحسم الافتراضي'
    )
    discount_reason = models.CharField(
        max_length=200, 
        blank=True, 
        verbose_name='سبب الحسم'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # ربط اختياري بحساب الذمم للطالب
    account = models.ForeignKey(
        'accounts.Account', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name='حساب الطالب (ذمم)'
    )

    class Meta:
        ordering = ['full_name']
        verbose_name = 'طالب'
        verbose_name_plural = 'الطلاب'

    def __str__(self):
        return self.full_name

    @property
    def ar_account(self):
        """Get or create the AR account for this student"""
        if self.account:
            return self.account
        
        # Create AR account if it doesn't exist
        from accounts.models import Account
        account = Account.get_or_create_student_ar_account(self)
        
        # Link the account to the student
        self.account = account
        self.save(update_fields=['account'])
        
        return account

    @property
    def has_account_link(self):
        """Check if student has an associated account"""
        return self.account is not None

    @property
    def grades(self):
        """جميع علامات الطالب"""
        return getattr(self, 'grade_set', None)
    
    @property
    def balance(self):
        """Calculate current AR balance for this student"""
        try:
            if not self.account:
                return Decimal('0')
            return self.account.get_net_balance()
        except Exception:
            return Decimal('0')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


# Signals: ensure AR account exists on create
from accounts.models import Account  # imported here to avoid circular during app loading


@receiver(post_save, sender=Student)
def ensure_student_ar_account(sender, instance, created, **kwargs):
    if created and not instance.account_id:
        try:
            ar = Account.get_or_create_student_ar_account(instance)
            instance.account_id = ar.id
            instance.save(update_fields=['account'])
        except Exception:
            pass
