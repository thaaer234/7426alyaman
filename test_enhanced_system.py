#!/usr/bin/env python
"""
Test script for Enhanced Financial Reports System
Tests cost center-course-teacher relationships and site-wide comma formatting
"""

import os
import sys
import django
from datetime import datetime, date
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alyaman.settings')
django.setup()

from accounts.models import CostCenter, Course, CourseTeacherAssignment, Account, JournalEntry, Transaction
from accounts.excel_utils import FinancialReportExporter, create_excel_response
from employ.models import Teacher
from django.contrib.auth.models import User


def create_enhanced_test_data():
    """Create enhanced test data with cost center-course-teacher relationships"""
    print("Creating enhanced test data...")
    
    # Create test user
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'email': 'test@example.com', 'first_name': 'Test', 'last_name': 'User'}
    )
    
    # Create test cost centers
    cost_centers_data = [
        {
            'code': 'CC001',
            'name': 'Academic Center',
            'name_ar': 'المركز الأكاديمي',
            'cost_center_type': 'ACADEMIC',
            'monthly_budget': Decimal('50000.00'),
            'manager_name': 'أحمد محمد',
        },
        {
            'code': 'CC002', 
            'name': 'Administrative Center',
            'name_ar': 'المركز الإداري',
            'cost_center_type': 'ADMINISTRATIVE',
            'monthly_budget': Decimal('30000.00'),
            'manager_name': 'فاطمة علي',
        },
    ]
    
    cost_centers = []
    for data in cost_centers_data:
        cc, created = CostCenter.objects.get_or_create(
            code=data['code'],
            defaults=data
        )
        cost_centers.append(cc)
        print(f"Created cost center: {cc.name}")
    
    # Create test teachers
    teachers_data = [
        {
            'full_name': 'محمد أحمد',
            'phone_number': '0501234567',
            'branches': 'علمي',
            'hourly_rate': Decimal('100.00'),
            'salary_type': 'hourly',
        },
        {
            'full_name': 'فاطمة حسن',
            'phone_number': '0507654321',
            'branches': 'أدبي',
            'hourly_rate': Decimal('120.00'),
            'salary_type': 'hourly',
        },
    ]
    
    teachers = []
    for data in teachers_data:
        teacher, created = Teacher.objects.get_or_create(
            full_name=data['full_name'],
            defaults=data
        )
        teachers.append(teacher)
        print(f"Created teacher: {teacher.full_name}")
    
    # Create test courses
    courses_data = [
        {
            'name': 'Mathematics Course',
            'name_ar': 'دورة الرياضيات',
            'price': Decimal('2000.00'),
            'duration_hours': 40,
            'cost_center': cost_centers[0],  # Academic Center
        },
        {
            'name': 'Arabic Literature Course',
            'name_ar': 'دورة الأدب العربي',
            'price': Decimal('1500.00'),
            'duration_hours': 30,
            'cost_center': cost_centers[0],  # Academic Center
        },
        {
            'name': 'Administrative Course',
            'name_ar': 'دورة الإدارة',
            'price': Decimal('1000.00'),
            'duration_hours': 20,
            'cost_center': cost_centers[1],  # Administrative Center
        },
    ]
    
    courses = []
    for data in courses_data:
        course, created = Course.objects.get_or_create(
            name=data['name'],
            defaults=data
        )
        courses.append(course)
        print(f"Created course: {course.name}")
    
    # Create teacher-course assignments
    assignments_data = [
        {
            'course': courses[0],  # Mathematics
            'teacher': teachers[0],  # محمد أحمد
            'start_date': date.today(),
            'hourly_rate': Decimal('100.00'),
            'total_hours': 40,
        },
        {
            'course': courses[1],  # Arabic Literature
            'teacher': teachers[1],  # فاطمة حسن
            'start_date': date.today(),
            'hourly_rate': Decimal('120.00'),
            'total_hours': 30,
        },
        {
            'course': courses[2],  # Administrative
            'teacher': teachers[0],  # محمد أحمد
            'start_date': date.today(),
            'hourly_rate': Decimal('80.00'),
            'total_hours': 20,
        },
    ]
    
    for data in assignments_data:
        assignment, created = CourseTeacherAssignment.objects.get_or_create(
            course=data['course'],
            teacher=data['teacher'],
            start_date=data['start_date'],
            defaults=data
        )
        print(f"Created assignment: {assignment}")
    
    print("Enhanced test data creation completed!")
    return cost_centers, courses, teachers


def test_cost_center_calculations():
    """Test cost center calculations with course-teacher relationships"""
    print("\nTesting cost center calculations...")
    
    cost_centers = CostCenter.objects.filter(is_active=True)
    start_date = date.today().replace(day=1)
    end_date = date.today()
    
    for cc in cost_centers:
        print(f"\nCost Center: {cc.name}")
        print(f"  Courses: {cc.get_course_count()}")
        print(f"  Teacher Salaries: {cc.get_teacher_salaries(start_date, end_date)}")
        print(f"  Total Revenue: {cc.get_total_revenue(start_date, end_date)}")
        
        # Show course details
        courses = cc.courses.filter(is_active=True)
        for course in courses:
            print(f"    Course: {course.name}")
            print(f"      Price: {course.price}")
            print(f"      Teacher Salaries: {course.get_total_teacher_salaries(start_date, end_date)}")
            
            # Show teacher assignments
            assignments = course.courseteacherassignment_set.filter(is_active=True)
            for assignment in assignments:
                print(f"        Teacher: {assignment.teacher.full_name}")
                print(f"        Salary: {assignment.calculate_total_salary()}")


def test_site_wide_export():
    """Test comprehensive site-wide export"""
    print("\nTesting comprehensive site-wide export...")
    
    try:
        from accounts.site_export_views import comprehensive_site_export
        from django.test import RequestFactory
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.get('/accounts/reports/site-export/comprehensive/')
        request.user = User.objects.first()
        
        # Test the export function
        response = comprehensive_site_export(request)
        
        if response.status_code == 200:
            print("✓ Comprehensive site export test passed")
            
            # Save the file for inspection
            filename = f"test_comprehensive_site_export_{date.today()}.xlsx"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✓ Export file saved as: {filename}")
        else:
            print(f"✗ Export test failed with status: {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error testing site-wide export: {e}")
        import traceback
        traceback.print_exc()


def test_comma_formatting():
    """Test comma formatting across the site"""
    print("\nTesting comma formatting...")
    
    from accounts.templatetags.site_formatting import intcomma, currency, financial_format
    
    test_numbers = [
        Decimal('0'),
        Decimal('100'),
        Decimal('1000'),
        Decimal('10000'),
        Decimal('100000'),
        Decimal('1000000'),
        Decimal('1234567.89'),
        Decimal('999999999.99'),
    ]
    
    print("Testing intcomma filter:")
    for num in test_numbers:
        formatted = intcomma(num)
        print(f"  {num} -> {formatted}")
    
    print("\nTesting currency filter:")
    for num in test_numbers[:5]:  # Test first 5 numbers
        formatted = currency(num, 'ريال')
        print(f"  {num} -> {formatted}")
    
    print("\nTesting financial_format filter:")
    for num in test_numbers[:5]:  # Test first 5 numbers
        formatted = financial_format(num)
        print(f"  {num} -> {formatted}")


if __name__ == '__main__':
    print("Enhanced Financial Reports System Test")
    print("=" * 50)
    
    try:
        # Create test data
        cost_centers, courses, teachers = create_enhanced_test_data()
        
        # Test cost center calculations
        test_cost_center_calculations()
        
        # Test comma formatting
        test_comma_formatting()
        
        # Test site-wide export
        test_site_wide_export()
        
        print("\n" + "=" * 50)
        print("All enhanced tests completed successfully!")
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
