from django import forms
from .models import Student
from django.forms import DateInput
from accounts.models import StudentReceipt, Studentenrollment

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = '__all__'
        widgets = {
            'birth_date': DateInput(attrs={'type': 'date'}),
            'registration_date': DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'discount_percent': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'discount_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'discount_reason': forms.TextInput(),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'how_knew_us': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'full_name': 'الاسم الكامل للطالب',
            'gender': 'الجنس',
            'branch': 'الصف الدراسي',
            'birth_date': 'تاريخ الميلاد',
            'tase3': 'مجموع الصف التاسع',
            'disease': 'الأمراض أو الحالات الصحية',
            'student_number': 'رقم الطالب',
            'nationality': 'الجنسية',
            'registration_date': 'تاريخ التسجيل',
            'father_name': 'اسم الأب',
            'father_job': 'مهنة الأب',
            'father_phone': 'هاتف الأب',
            'mother_name': 'اسم الأم',
            'mother_job': 'مهنة الأم',
            'mother_phone': 'هاتف الأم',
            'address': 'العنوان',
            'home_phone': 'هاتف المنزل',
            'previous_school': 'المدرسة السابقة',
            'elementary_school': 'المدرسة الابتدائية',
            'how_knew_us': 'كيفية معرفة المعهد',
            'notes': 'ملاحظات',
            'discount_percent': 'نسبة الحسم الافتراضي %',
            'discount_amount': 'قيمة الحسم الافتراضي',
            'discount_reason': 'سبب الحسم',
            'email': 'البريد الإلكتروني',
            'phone': 'رقم الهاتف',
            'is_active': 'نشط'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # جعل الحقول المطلوبة فقط الأساسية
        required_fields = {
            'full_name', 'gender', 'branch', 'birth_date', 'student_number', 
            'nationality', 'registration_date', 'father_name', 'father_phone'
        }
        
        for field_name, field in self.fields.items():
            field.required = field_name in required_fields
            field.widget.attrs.update({'class': 'form-control'})
        
        # إزالة حقل added_by من النموذج لأنه سيتم تعبئته تلقائيًا
        if 'added_by' in self.fields:
            self.fields.pop('added_by')
        
        # إزالة حقل account من النموذج لأنه سيتم إنشاؤه تلقائيًا
        if 'account' in self.fields:
            self.fields.pop('account')
            
        # تخصيص خيارات القوائم المنسدلة
        self.fields['gender'].choices = [
            ('', 'اختر الجنس'),
            ('male', 'ذكر'),
            ('female', 'أنثى')
        ]
        
        self.fields['branch'].choices = [
            ('', 'اختر الصف الدراسي'),
            ('أدبي', 'الأدبي'),
            ('علمي', 'العلمي'),
            ('تاسع', 'الصف التاسع')
        ]
        
        self.fields['how_knew_us'].choices = [
            ('', 'اختر طريقة المعرفة'),
            ('friend', 'صديق'),
            ('social', 'وسائل التواصل الاجتماعي'),
            ('ad', 'إعلان'),
            ('ads', 'إعلانات طرقية'),
            ('other', 'أخرى')
        ]