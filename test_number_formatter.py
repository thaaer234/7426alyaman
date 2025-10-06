#!/usr/bin/env python
"""
Test script for Number Formatter Plugin
Tests the JavaScript plugin functionality
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alyaman.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse


def test_number_formatter_demo():
    """Test the number formatter demo page"""
    print("Testing Number Formatter Demo Page...")
    
    # Create test client
    client = Client()
    
    # Create test user
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'email': 'test@example.com', 'first_name': 'Test', 'last_name': 'User'}
    )
    
    # Login user
    client.force_login(user)
    
    try:
        # Test demo page access
        response = client.get('/accounts/reports/number-formatter-demo/')
        
        if response.status_code == 200:
            print("✓ Demo page loads successfully")
            
            # Check if JavaScript file is referenced
            if 'number-formatter.js' in response.content.decode():
                print("✓ JavaScript file is included")
            else:
                print("✗ JavaScript file not found")
            
            # Check if CSS file is referenced
            if 'number-formatter.css' in response.content.decode():
                print("✓ CSS file is included")
            else:
                print("✗ CSS file not found")
            
            # Check for data attributes
            if 'data-number-format' in response.content.decode():
                print("✓ Data attributes are present")
            else:
                print("✗ Data attributes not found")
                
        else:
            print(f"✗ Demo page failed with status: {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error testing demo page: {e}")


def test_static_files():
    """Test if static files exist"""
    print("\nTesting Static Files...")
    
    static_files = [
        'static/js/number-formatter.js',
        'static/css/number-formatter.css'
    ]
    
    for file_path in static_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} exists")
            
            # Check file size
            size = os.path.getsize(file_path)
            print(f"  File size: {size} bytes")
            
        else:
            print(f"✗ {file_path} not found")


def test_template_tags():
    """Test template tags functionality"""
    print("\nTesting Template Tags...")
    
    try:
        from accounts.templatetags.number_formatter_tags import add_number_formatting, auto_format_inputs
        
        print("✓ Template tags imported successfully")
        
        # Test filter function
        class MockField:
            def __init__(self):
                self.field = MockFieldField()
        
        class MockFieldField:
            def __init__(self):
                self.widget = MockWidget()
        
        class MockWidget:
            def __init__(self):
                self.attrs = {}
        
        mock_field = MockField()
        result = add_number_formatting(mock_field, 'currency')
        
        if hasattr(result.field.widget, 'attrs') and 'data-number-format' in result.field.widget.attrs:
            print("✓ add_number_formatting filter works")
        else:
            print("✗ add_number_formatting filter failed")
            
    except Exception as e:
        print(f"✗ Error testing template tags: {e}")


def test_url_routes():
    """Test URL routes"""
    print("\nTesting URL Routes...")
    
    try:
        from django.urls import reverse
        
        # Test demo page URL
        url = reverse('accounts:number_formatter_demo')
        if url == '/accounts/reports/number-formatter-demo/':
            print("✓ Demo page URL is correct")
        else:
            print(f"✗ Demo page URL incorrect: {url}")
            
    except Exception as e:
        print(f"✗ Error testing URL routes: {e}")


if __name__ == '__main__':
    print("Number Formatter Plugin Test")
    print("=" * 50)
    
    try:
        # Test static files
        test_static_files()
        
        # Test template tags
        test_template_tags()
        
        # Test URL routes
        test_url_routes()
        
        # Test demo page
        test_number_formatter_demo()
        
        print("\n" + "=" * 50)
        print("Number Formatter Plugin tests completed!")
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
